#!/usr/bin/env python3
"""Diagnostic: open the crawl start_url and report what the page ACTUALLY contains.

Run this when a crawl reports "found 0 book links". It saves a screenshot and
the page HTML, and prints the page title plus a sample of the links on the page
so the correct CSS selectors can be worked out.

    python3 diagnose.py

Outputs (next to this file):
    debug_page.png    - screenshot of what the browser saw
    debug_page.html   - full HTML of the page
"""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from bookbot.utils import find_chromium, load_config, setup_logging, log

BOT_WALL_MARKERS = [
    "just a moment", "attention required", "cf-browser-verification",
    "verify you are human", "enable javascript and cookies", "captcha",
    "access denied", "request blocked",
]


def main() -> None:
    setup_logging()
    cfg = load_config("config.yaml")
    url = cfg["crawl"]["start_url"]
    sel = cfg["crawl"]["book_link_selector"]

    with sync_playwright() as p:
        kwargs = {"headless": cfg["run"].get("headless", True)}
        chromium = find_chromium(cfg["run"].get("chromium_path"))
        if chromium:
            kwargs["executable_path"] = chromium
        browser = p.chromium.launch(**kwargs)
        page = browser.new_context(user_agent=cfg["run"].get("user_agent")).new_page()

        log.info("Opening %s", url)
        page.goto(url, timeout=cfg["run"]["nav_timeout"] * 1000, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        for _ in range(4):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(600)

        page.screenshot(path="debug_page.png", full_page=True)
        html = page.content()
        with open("debug_page.html", "w", encoding="utf-8") as fh:
            fh.write(html)

        title = page.title()
        body_lc = (page.inner_text("body") or "").lower()[:3000]

        print("\n================ PAGE DIAGNOSIS ================")
        print("Title:", title or "(empty)")
        print("Final URL:", page.url)

        hit = next((m for m in BOT_WALL_MARKERS if m in title.lower() or m in body_lc), None)
        if hit:
            print(f"\n⚠️  BOT-PROTECTION WALL DETECTED (matched: '{hit}')")
            print("    SolutionInn is blocking automated browsers. Crawling will")
            print("    not work without an official API or anti-bot handling.")

        # How many links match the current selector?
        matched = page.query_selector_all(sel)
        print(f"\nLinks matching current selector  {sel!r}:  {len(matched)}")

        # Show the most common href path patterns so we can pick a real selector.
        hrefs = [a.get_attribute("href") or "" for a in page.query_selector_all("a[href]")]
        print(f"Total <a href> on page: {len(hrefs)}")
        prefixes = Counter()
        for h in hrefs:
            path = urlparse(h).path
            seg = "/" + path.strip("/").split("/")[0] if path.strip("/") else "/"
            prefixes[seg] += 1
        print("\nMost common link path prefixes (first segment -> count):")
        for seg, n in prefixes.most_common(15):
            print(f"   {n:4d}  {seg}/...")

        print("\nSample of the first 25 links on the page:")
        for h in hrefs[:25]:
            print("   ", h[:100])

        print("\nSaved: debug_page.png  and  debug_page.html")
        print("Send those two files (or the output above) back to continue.")
        print("===============================================\n")
        browser.close()


if __name__ == "__main__":
    main()
