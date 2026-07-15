#!/usr/bin/env python3
"""Take a folder of book PDFs, grab ONE random page from each, and save it as an
image named after the book — all into a single parent folder.

    input folder:   book_pdfs/                (put your 100 PDFs here)
    output folder:  book random page image/   (one image per book)
                        Introduction to Algorithms.png
                        Campbell Biology.png
                        ...

Usage:
    python3 pdf_to_images.py
    python3 pdf_to_images.py --input book_pdfs --output "book random page image"
    python3 pdf_to_images.py --format jpg --zoom 2.5
    python3 pdf_to_images.py --page-min 10 --page-max 15   # restrict page range

The image's file name is the PDF's file name (the book's name). No web access,
no search — it just reads the PDFs you provide.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF


def safe_name(stem: str) -> str:
    """Keep the book name but strip characters that are illegal in file names."""
    name = re.sub(r'[\\/:*?"<>|]+', " ", stem).strip()
    name = re.sub(r"\s+", " ", name)
    return name or "book"


def pick_page(page_count: int, page_min: int | None, page_max: int | None) -> int:
    """Return a 0-indexed page. Random over the whole book unless a range is set."""
    lo = page_min if page_min else 1
    hi = page_max if page_max else page_count
    lo = max(1, min(lo, page_count))
    hi = max(lo, min(hi, page_count))
    return random.randint(lo, hi) - 1


def render_random_page(pdf_path, out_dir, fmt: str = "png", zoom: float = 2.0,
                       page_min: int | None = None, page_max: int | None = None) -> dict:
    """Render one random page of a single PDF to an image named after the book.

    Returns {'book', 'page', 'image', 'status', 'error'}. Never raises.
    """
    from pathlib import Path as _Path
    pdf_path = _Path(pdf_path)
    out_dir = _Path(out_dir)
    book = safe_name(pdf_path.stem)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            raise ValueError("PDF has no pages")
        idx = pick_page(doc.page_count, page_min, page_max)
        pix = doc.load_page(idx).get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        image = out_dir / f"{book}.{fmt}"
        pix.save(image)
        doc.close()
        return {"book": book, "page": idx + 1, "image": str(image),
                "status": "ok", "error": ""}
    except Exception as exc:
        return {"book": book, "page": None, "image": "",
                "status": "failed", "error": str(exc)}


def process_folder(in_dir, out_dir, fmt: str = "png", zoom: float = 2.0,
                   page_min: int | None = None, page_max: int | None = None) -> list[dict]:
    """Render one random page for every PDF in a folder. Returns per-book results."""
    from pathlib import Path as _Path
    pdfs = sorted(_Path(in_dir).rglob("*.pdf"))
    return [render_random_page(p, out_dir, fmt, zoom, page_min, page_max) for p in pdfs]


def main() -> None:
    ap = argparse.ArgumentParser(description="Save one random page image per book PDF.")
    ap.add_argument("--input", default="book_pdfs", help="folder containing the book PDFs")
    ap.add_argument("--output", default="book random page image", help="parent folder for the images")
    ap.add_argument("--format", default="png", choices=["png", "jpg"], help="image format")
    ap.add_argument("--zoom", type=float, default=2.0, help="render scale (higher = sharper)")
    ap.add_argument("--page-min", type=int, default=None, help="earliest page allowed (1-indexed)")
    ap.add_argument("--page-max", type=int, default=None, help="latest page allowed (1-indexed)")
    ap.add_argument("--seed", type=int, default=None, help="fix the random seed (reproducible)")
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    in_dir = Path(args.input)
    out_dir = Path(args.output)
    if not in_dir.is_dir():
        print(f"❌ Input folder '{in_dir}' does not exist.")
        print(f"   Create it and put your PDF files inside, then run again:")
        print(f"       mkdir -p '{in_dir}'")
        sys.exit(1)

    pdfs = sorted(in_dir.rglob("*.pdf"))
    if not pdfs:
        print(f"❌ No .pdf files found in '{in_dir}'. Put your book PDFs there and re-run.")
        sys.exit(1)

    print(f"Found {len(pdfs)} PDF(s) in '{in_dir}'.")
    print(f"Saving images into '{out_dir}/'\n")

    results = process_folder(in_dir, out_dir, args.format, args.zoom,
                             args.page_min, args.page_max)

    ok = 0
    failed: list[str] = []
    for i, r in enumerate(results, 1):
        if r["status"] == "ok":
            print(f"[{i}/{len(results)}] {r['book']}  ->  page {r['page']}  ->  {Path(r['image']).name}")
            ok += 1
        else:
            print(f"[{i}/{len(results)}] {r['book']}  ->   SKIPPED ({r['error']})")
            failed.append(r["book"])

    print(f"\n✅ Done. {ok} image(s) saved in '{out_dir}/'.")
    if failed:
        print(f"⚠️  {len(failed)} PDF(s) could not be read: {', '.join(failed[:10])}"
              + (" ..." if len(failed) > 10 else ""))


if __name__ == "__main__":
    main()
