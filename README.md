# book-images

A bot that walks SolutionInn's textbook listings from first to last book and, for
each book, searches the web for a PDF, renders **one** page (somewhere between
page 10 and 15) to an image, and saves it in a folder named after the book.

```
output/
  calculus-early-transcendentals/
    calculus-early-transcendentals_p12.png
  introduction-to-algorithms/
    introduction-to-algorithms_p12.png
  ...
  manifest.csv        <- log of every book: what was found and where it was saved
```

## How it works

1. **Crawl** (`bookbot/crawler.py`) — opens the SolutionInn listing page and
   collects each book's title + link, following "next page" links up to a cap.
2. **Search** (`bookbot/finder.py`) — for each title, runs a Google search
   (`"<title> pdf filetype:pdf"`) and collects candidate result links, PDFs
   first. Google often blocks automated queries, so a DuckDuckGo fallback is
   built in.
3. **Capture** (`bookbot/capture.py`) — downloads each candidate, verifies it's a
   real PDF, picks a page in the 10–15 range (clamped to the document length),
   and renders that single page to an image with PyMuPDF.
4. **Record** (`bookbot/pipeline.py`) — writes a row to `manifest.csv`. Re-running
   skips books already marked `ok`, so you can stop and resume.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Where the book list comes from

SolutionInn's public site is behind **Cloudflare's bot wall** — an automated
browser gets a "Just a moment…" challenge page instead of the book list, so
crawling it directly does not work. Run `python diagnose.py` to see this for
yourself. There are two supported sources (set `crawl.source` in `config.yaml`):

- **`file` (default, reliable):** the bot reads `books.csv` — a CSV with a
  `title` column, or just one book title per line. Export this list from
  SolutionInn's own database / admin / sitemap and drop it in. Cloudflare is
  never involved.
- **`site` (blocked):** crawl SolutionInn directly. Left in for completeness,
  but it will not work while the site is behind Cloudflare unless the scraper's
  IP/user-agent is allow-listed, or an official API is used.

## Run

```bash
python run.py                 # full run using config.yaml (file mode by default)
python run.py --limit 5       # only the first 5 books (good first test)
python run.py --headed        # watch the browser (useful for debugging)
python run.py --config my.yaml
```

Edit `books.csv` to list the books you want, then run the commands above.

## Configuration

Everything is in `config.yaml` — no need to edit code. Key knobs:

| Setting | Meaning |
| --- | --- |
| `crawl.start_url` | SolutionInn listing page to start from |
| `crawl.book_link_selector` | CSS selector for book links on a listing page |
| `crawl.next_page_selector` | CSS selector for the "next page" link |
| `crawl.max_pages` / `max_books` | how far to crawl |
| `search.engine` | `google` (with automatic `duckduckgo` fallback) |
| `capture.page_min` / `page_max` | page range to choose from (default 10–15) |
| `capture.page_pick` | `middle` (default), `random`, or an exact page number |
| `capture.zoom` | render sharpness (2.0 ≈ 144 DPI) |
| `run.headless` | `false` to watch the browser |
| `run.delay_seconds` / `delay_jitter` | polite pause between books |

## Things to know (please read)

- **Selectors will need tuning.** SolutionInn's HTML changes over time and I
  couldn't validate the live DOM from the build sandbox (outbound browsing was
  blocked there). If a run reports "found 0 book links", open `start_url` in a
  browser, inspect a book link, and update `crawl.book_link_selector` /
  `next_page_selector` in `config.yaml`.
- **Google scraping is fragile by nature.** Google shows CAPTCHAs to automated
  traffic; when that happens the bot logs it and falls back to DuckDuckGo. For a
  large, reliable run, consider a proper search API (Bing/SerpAPI) — the finder
  is structured so a new engine is easy to add.
- **A matching PDF may not exist** for every title; those books are recorded in
  the manifest with status `no_pdf` / `no_results` and simply skipped.
- **Copyright.** This tool downloads third-party PDFs found via web search, many
  of which are copyrighted textbooks. Use it only where you have the right to do
  so (e.g. content you own or are licensed for). If the goal is SolutionInn's own
  catalog, pointing the capture step at SolutionInn's own preview PDFs is more
  reliable and avoids this issue — say the word and I'll wire that path in.

## Layout

```
run.py                 CLI entry point
config.yaml            all settings
requirements.txt       dependencies
bookbot/
  crawler.py           crawl SolutionInn -> [ {title, url} ]
  finder.py            title -> candidate PDF URLs (Google / DuckDuckGo)
  capture.py           PDF URL -> one rendered page image
  pipeline.py          orchestrates crawl -> search -> capture -> manifest
  utils.py             config, logging, slugify, resume manifest
```
