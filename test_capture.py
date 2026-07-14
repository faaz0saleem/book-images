#!/usr/bin/env python3
"""Proof test: fetch a REAL multi-page book/PDF from real websites and save a
page image from the 10-15 range — no search engine involved.

This isolates the core capability ("grab a page of a book and turn it into an
image") from the fragile web-search step. If this produces an image, the
download + render engine works on your network.

    python3 test_capture.py

Output: an image under  output/real-capture-test/
"""

from __future__ import annotations

from pathlib import Path

from bookbot.capture import capture_from_candidates
from bookbot.utils import load_config, setup_logging, log

# Real, freely-downloadable, multi-page PDFs on real public websites.
# The capture code tries them in order and uses the first that works.
REAL_PDFS = [
    "https://arxiv.org/pdf/1706.03762",                 # open-access paper, 15 pages
    "https://www.irs.gov/pub/irs-pdf/i1040gi.pdf",      # US gov (public domain), ~110 pages
    "https://www.gutenberg.org/cache/epub/1342/pg1342.pdf",  # Pride & Prejudice (public domain)
    "https://css4.pub/2015/textbook/somatosensory.pdf", # sample textbook PDF
]


def main() -> None:
    setup_logging()
    cfg = load_config("config.yaml")
    log.info("Testing real download + page render (pages %s-%s)...",
             cfg["capture"]["page_min"], cfg["capture"]["page_max"])

    result = capture_from_candidates(REAL_PDFS, "Real Capture Test", cfg)

    print("\n==================== RESULT ====================")
    if result["status"] == "ok":
        p = Path(result["image_path"])
        print("✅ SUCCESS — the bot fetched a real book and saved a page image.")
        print("   Source PDF :", result["pdf_url"])
        print("   Page saved :", result["page"])
        print("   Image file :", p, f"({p.stat().st_size} bytes)")
        print("\nOpen that PNG to see the captured page.")
    else:
        print("❌ Could not capture from any test URL.")
        print("   status:", result["status"], "-", result["note"])
        print("   If every URL failed to download, your network may block them;")
        print("   try again on a normal connection.")
    print("===============================================\n")


if __name__ == "__main__":
    main()
