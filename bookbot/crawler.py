"""Crawl SolutionInn listing pages and collect (title, url) for each book."""

from __future__ import annotations

from urllib.parse import urljoin

from .utils import log


def _dismiss_consent(page) -> None:
    """Best-effort click of common cookie/consent buttons."""
    for text in ("Accept", "Accept all", "I agree", "Got it", "Allow all"):
        try:
            btn = page.get_by_role("button", name=text)
            if btn.count() > 0:
                btn.first.click(timeout=2000)
                return
        except Exception:
            pass


def crawl_books(page, cfg: dict) -> list[dict]:
    """Return a de-duplicated list of {'title', 'url'} dicts from the listings.

    `page` is an already-open Playwright page. Selectors come from config so
    the crawler can be retargeted without code changes.
    """
    c = cfg["crawl"]
    nav_timeout = cfg["run"]["nav_timeout"] * 1000

    books: list[dict] = []
    seen: set[str] = set()
    url = c["start_url"]
    max_books = c.get("max_books", 0) or 10**9

    for page_num in range(1, c.get("max_pages", 1) + 1):
        if not url:
            break
        log.info("Crawling listing page %d: %s", page_num, url)
        try:
            page.goto(url, timeout=nav_timeout, wait_until="domcontentloaded")
        except Exception as exc:
            log.warning("Could not load %s (%s)", url, exc)
            break
        _dismiss_consent(page)

        links = page.query_selector_all(c["book_link_selector"])
        log.info("  found %d book links", len(links))
        for a in links:
            href = a.get_attribute("href")
            if not href:
                continue
            full = urljoin(url, href)
            if full in seen:
                continue

            title = None
            if c.get("title_selector"):
                node = a.query_selector(c["title_selector"])
                if node:
                    title = (node.inner_text() or "").strip()
            if not title:
                title = (a.inner_text() or a.get_attribute("title") or "").strip()
            if not title:
                continue

            seen.add(full)
            books.append({"title": title, "url": full})
            if len(books) >= max_books:
                log.info("Reached max_books=%d", max_books)
                return books

        # find the next listing page
        next_url = None
        if c.get("next_page_selector"):
            nxt = page.query_selector(c["next_page_selector"])
            if nxt:
                href = nxt.get_attribute("href")
                if href:
                    next_url = urljoin(url, href)
        url = next_url

    return books
