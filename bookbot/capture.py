"""Download a candidate PDF and render ONE page (10-15) to an image."""

from __future__ import annotations

import random
from pathlib import Path

import fitz  # PyMuPDF
import requests

from .utils import log, slugify


def _pick_page(page_count: int, cfg: dict) -> int:
    """Choose a 0-indexed page within [page_min, page_max], clamped to the PDF."""
    c = cfg["capture"]
    lo, hi = int(c["page_min"]), int(c["page_max"])
    pick = c.get("page_pick", "middle")
    if isinstance(pick, int):
        one_based = pick
    elif pick == "random":
        one_based = random.randint(lo, hi)
    else:  # "middle"
        one_based = (lo + hi) // 2
    # Clamp to what the document actually has (1..page_count).
    one_based = max(1, min(one_based, page_count))
    return one_based - 1


def _download(url: str, dest: Path, cfg: dict) -> bool:
    """Stream a URL to disk if it is actually a PDF and within the size cap."""
    timeout = cfg["run"]["request_timeout"]
    max_bytes = cfg["capture"]["max_pdf_mb"] * 1024 * 1024
    headers = {"User-Agent": cfg["run"]["user_agent"]}
    try:
        with requests.get(url, stream=True, timeout=timeout, headers=headers) as r:
            r.raise_for_status()
            ctype = r.headers.get("Content-Type", "").lower()
            # Accept explicit PDFs or .pdf URLs; reject obvious HTML pages.
            if "pdf" not in ctype and not url.lower().split("?")[0].endswith(".pdf"):
                log.info("    not a pdf (Content-Type: %s)", ctype or "unknown")
                return False
            size = 0
            with dest.open("wb") as fh:
                for chunk in r.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > max_bytes:
                        log.info("    too large (>%d MB), skipping", cfg["capture"]["max_pdf_mb"])
                        return False
                    fh.write(chunk)
        # Sanity check: real PDFs start with %PDF.
        with dest.open("rb") as fh:
            if fh.read(5)[:4] != b"%PDF":
                log.info("    downloaded file is not a valid PDF")
                return False
        return True
    except Exception as exc:
        log.info("    download failed: %s", exc)
        return False


def capture_from_candidates(candidates: list[str], title: str, cfg: dict) -> dict:
    """Try each candidate until one yields a rendered page image.

    Returns {'status', 'pdf_url', 'page', 'image_path', 'note'}.
    """
    out_root = Path(cfg["output"]["dir"])
    slug = slugify(title)
    book_dir = out_root / slug
    book_dir.mkdir(parents=True, exist_ok=True)

    fmt = cfg["capture"].get("image_format", "png").lower()
    zoom = float(cfg["capture"].get("zoom", 2.0))
    tmp_pdf = book_dir / "_candidate.pdf"

    for url in candidates:
        log.info("  trying candidate: %s", url)
        if not _download(url, tmp_pdf, cfg):
            continue
        try:
            doc = fitz.open(tmp_pdf)
        except Exception as exc:
            log.info("    could not open pdf: %s", exc)
            continue
        try:
            if doc.page_count == 0:
                continue
            idx = _pick_page(doc.page_count, cfg)
            pix = doc.load_page(idx).get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img_path = book_dir / f"{slug}_p{idx + 1}.{fmt}"
            pix.save(img_path)
        except Exception as exc:
            log.info("    could not render page: %s", exc)
            doc.close()
            continue
        doc.close()
        tmp_pdf.unlink(missing_ok=True)
        log.info("  saved %s (page %d)", img_path, idx + 1)
        return {
            "status": "ok",
            "pdf_url": url,
            "page": idx + 1,
            "image_path": str(img_path),
            "note": "",
        }

    tmp_pdf.unlink(missing_ok=True)
    return {"status": "no_pdf", "pdf_url": "", "page": "", "image_path": "",
            "note": "no usable PDF among candidates"}
