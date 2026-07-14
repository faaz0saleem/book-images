"""Tie the stages together: crawl -> search -> capture -> record."""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from .capture import capture_from_candidates
from .crawler import crawl_books
from .finder import find_pdf_candidates
from .utils import Manifest, find_chromium, log, polite_sleep, slugify


def run(cfg: dict) -> None:
    run_cfg = cfg["run"]
    manifest = Manifest(cfg["output"]["manifest"])

    with sync_playwright() as p:
        launch_kwargs = {"headless": run_cfg.get("headless", True)}
        chromium_path = find_chromium(run_cfg.get("chromium_path"))
        if chromium_path:
            log.info("Using Chromium at %s", chromium_path)
            launch_kwargs["executable_path"] = chromium_path
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(user_agent=run_cfg.get("user_agent"))
        page = context.new_page()
        page.set_default_navigation_timeout(run_cfg["nav_timeout"] * 1000)

        # 1) Collect the book list (first to last).
        books = crawl_books(page, cfg)
        log.info("Collected %d book(s) total", len(books))

        # 2) For each book: search -> capture one page image.
        for i, book in enumerate(books, 1):
            title, source_url = book["title"], book["url"]
            slug = slugify(title)
            log.info("[%d/%d] %s", i, len(books), title)

            if manifest.already_done(slug):
                log.info("  already done, skipping")
                continue

            try:
                candidates = find_pdf_candidates(page, title, cfg)
                if not candidates:
                    manifest.record(slug=slug, title=title, source_url=source_url,
                                    status="no_results", note="search returned nothing")
                else:
                    result = capture_from_candidates(candidates, title, cfg)
                    manifest.record(slug=slug, title=title, source_url=source_url,
                                    **result)
            except Exception as exc:
                log.warning("  error handling book: %s", exc)
                manifest.record(slug=slug, title=title, source_url=source_url,
                                status="error", note=str(exc)[:200])

            polite_sleep(run_cfg["delay_seconds"], run_cfg["delay_jitter"])

        context.close()
        browser.close()

    log.info("Done. See %s", cfg["output"]["manifest"])
