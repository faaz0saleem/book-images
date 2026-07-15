"""Find candidate PDF URLs for a book title using a web search engine.

As requested, Google is the primary engine. Google aggressively blocks
automated queries, so a DuckDuckGo HTML fallback is included (controlled by
config). Both return a de-duplicated, ranked list of candidate URLs that look
like they point at a PDF.
"""

from __future__ import annotations

from urllib.parse import quote_plus, urlparse, parse_qs, unquote

from .utils import log


def _looks_like_pdf(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".pdf") or ".pdf" in url.lower()


def _build_query(title: str, cfg: dict) -> str:
    q = cfg["search"]["query_template"].format(title=title)
    if cfg["search"].get("prefer_filetype_pdf"):
        q += " filetype:pdf"
    return q


def _google(page, query: str, nav_timeout: int, limit: int) -> list[str]:
    url = f"https://www.google.com/search?q={quote_plus(query)}&num=20&hl=en"
    page.goto(url, timeout=nav_timeout, wait_until="domcontentloaded")

    # Consent interstitial (common in EU / fresh sessions).
    for text in ("Accept all", "I agree", "Accept"):
        try:
            btn = page.get_by_role("button", name=text)
            if btn.count() > 0:
                btn.first.click(timeout=2000)
                page.wait_for_load_state("domcontentloaded")
                break
        except Exception:
            pass

    body = (page.inner_text("body") or "").lower()
    if "unusual traffic" in body or "are not a robot" in body or "/sorry/" in page.url:
        log.warning("  Google is showing a CAPTCHA / blocked page")
        return []

    hrefs = []
    for a in page.query_selector_all("a"):
        href = a.get_attribute("href") or ""
        # Google sometimes wraps results as /url?q=<real>&...
        if href.startswith("/url?"):
            qs = parse_qs(urlparse(href).query)
            if "q" in qs:
                href = qs["q"][0]
        if href.startswith("http"):
            hrefs.append(href)
    return _rank(hrefs, limit)


def _duckduckgo(page, query: str, nav_timeout: int, limit: int) -> list[str]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    page.goto(url, timeout=nav_timeout, wait_until="domcontentloaded")
    hrefs = []
    for a in page.query_selector_all("a.result__a, a[href]"):
        href = a.get_attribute("href") or ""
        # DDG HTML wraps external links as /l/?uddg=<encoded>
        if "uddg=" in href:
            qs = parse_qs(urlparse(href).query)
            if "uddg" in qs:
                href = unquote(qs["uddg"][0])
        if href.startswith("http"):
            hrefs.append(href)
    return _rank(hrefs, limit)


def _rank(hrefs: list[str], limit: int) -> list[str]:
    """De-dupe, drop search-engine self links, put obvious PDFs first."""
    skip_hosts = ("google.", "duckduckgo.", "gstatic.", "youtube.", "webcache.")
    pdfs, others, seen = [], [], set()
    for h in hrefs:
        if h in seen:
            continue
        host = urlparse(h).netloc.lower()
        if any(s in host for s in skip_hosts):
            continue
        seen.add(h)
        (pdfs if _looks_like_pdf(h) else others).append(h)
    return (pdfs + others)[:limit]


def find_pdf_candidates(page, title: str, cfg: dict) -> list[str]:
    """Return up to max_candidates candidate URLs likely to be a PDF."""
    query = _build_query(title, cfg)
    nav_timeout = cfg["run"]["nav_timeout"] * 1000
    limit = cfg["search"].get("max_candidates", 5)
    log.info("  searching: %s", query)

    candidates: list[str] = []
    if cfg["search"].get("engine", "google") == "google":
        try:
            candidates = _google(page, query, nav_timeout, limit)
        except Exception as exc:
            log.warning("  google search failed: %s", exc)

    if not candidates and cfg["search"].get("fallback_to_duckduckgo", True):
        log.info("  falling back to DuckDuckGo")
        try:
            candidates = _duckduckgo(page, query, nav_timeout, limit)
        except Exception as exc:
            log.warning("  duckduckgo search failed: %s", exc)

    log.info("  %d candidate link(s)", len(candidates))
    return candidates
