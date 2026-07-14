"""Decide where the book list comes from: crawl the site, or read a file.

Crawling SolutionInn's public site is blocked by Cloudflare's bot wall, so the
reliable path is to feed the bot a list you export internally (a CSV or a plain
text file of titles). This module dispatches between the two based on config.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .crawler import crawl_books
from .utils import log


def load_books_from_file(path: str) -> list[dict]:
    """Read books from a .csv (columns: title[,url]) or .txt (one title/line).

    Returns a list of {'title', 'url'} dicts. `url` may be empty — only the
    title is needed, since the finder searches the web by title.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"books_file '{path}' not found. Create it (one book title per line, "
            f"or a CSV with a 'title' column) or set crawl.source back to 'site'."
        )

    books: list[dict] = []
    if p.suffix.lower() == ".csv":
        with p.open("r", newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            # Support a headerless single-column file too.
            if reader.fieldnames and any(
                (f or "").strip().lower() == "title" for f in reader.fieldnames
            ):
                title_key = next(f for f in reader.fieldnames
                                 if (f or "").strip().lower() == "title")
                url_key = next((f for f in reader.fieldnames
                                if (f or "").strip().lower() in ("url", "link")), None)
                for row in reader:
                    title = (row.get(title_key) or "").strip()
                    if title:
                        books.append({"title": title,
                                      "url": (row.get(url_key) or "").strip() if url_key else ""})
            else:
                fh.seek(0)
                for row in csv.reader(fh):
                    if row and row[0].strip():
                        books.append({"title": row[0].strip(),
                                      "url": row[1].strip() if len(row) > 1 else ""})
    else:  # plain text, one title per line
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            title = line.strip()
            if title and not title.startswith("#"):
                books.append({"title": title, "url": ""})

    log.info("Loaded %d book(s) from %s", len(books), path)
    return books


def get_books(page, cfg: dict) -> list[dict]:
    """Return the book list from whichever source config selects."""
    source = cfg["crawl"].get("source", "site").lower()
    if source == "file":
        books = load_books_from_file(cfg["crawl"].get("books_file", "books.csv"))
        max_books = cfg["crawl"].get("max_books", 0) or 0
        if max_books and len(books) > max_books:
            books = books[:max_books]
        return books
    return crawl_books(page, cfg)
