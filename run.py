#!/usr/bin/env python3
"""Entry point for the book-images bot.

Usage:
    python run.py                 # use config.yaml
    python run.py --config my.yaml
    python run.py --headed        # watch the browser (overrides config)
    python run.py --limit 5       # cap number of books (quick test)

First-time setup:
    pip install -r requirements.txt
    playwright install chromium
"""

from __future__ import annotations

import argparse

from bookbot.pipeline import run
from bookbot.utils import load_config, setup_logging


def main() -> None:
    ap = argparse.ArgumentParser(description="Crawl SolutionInn and save one page image per book.")
    ap.add_argument("--config", default="config.yaml", help="path to config file")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--limit", type=int, default=None, help="max number of books (overrides max_books)")
    args = ap.parse_args()

    setup_logging()
    cfg = load_config(args.config)
    if args.headed:
        cfg["run"]["headless"] = False
    if args.limit is not None:
        cfg["crawl"]["max_books"] = args.limit

    run(cfg)


if __name__ == "__main__":
    main()
