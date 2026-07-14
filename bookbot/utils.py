"""Small shared helpers: logging, config loading, slugifying, checkpointing."""

from __future__ import annotations

import csv
import logging
import os
import random
import re
import time
from pathlib import Path

import yaml

log = logging.getLogger("bookbot")


def setup_logging(verbose: bool = True) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_len: int = 80) -> str:
    """Turn a book title into a safe folder/file name."""
    text = (text or "").strip().lower()
    slug = _slug_re.sub("-", text).strip("-")
    if not slug:
        slug = "book"
    return slug[:max_len].rstrip("-")


def polite_sleep(base: float, jitter: float) -> None:
    """Wait base + random(0..jitter) seconds so we don't hammer any server."""
    time.sleep(base + random.random() * jitter)


class Manifest:
    """CSV record of every book we've handled, doubling as a resume checkpoint."""

    FIELDS = ["slug", "title", "source_url", "pdf_url", "page", "image_path", "status", "note"]

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._done_slugs: set[str] = set()
        if self.path.exists():
            with self.path.open("r", newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    if row.get("status") == "ok":
                        self._done_slugs.add(row["slug"])
        else:
            with self.path.open("w", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=self.FIELDS).writeheader()

    def already_done(self, slug: str) -> bool:
        return slug in self._done_slugs

    def record(self, **row) -> None:
        clean = {k: row.get(k, "") for k in self.FIELDS}
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=self.FIELDS).writerow(clean)
        if clean.get("status") == "ok":
            self._done_slugs.add(clean["slug"])
