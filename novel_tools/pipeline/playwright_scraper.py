"""Playwright-based novel scraper for sites with JS-rendered content (trxs.cc).

pip install playwright && python -m playwright install chromium
"""

import re
import time
from pathlib import Path
from typing import Optional


def _get_browser():
    """Lazy-init playwright browser."""
    from playwright.sync_api import sync_playwright
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    return p, browser


def scrape_trxs_books(max_books: int = 15) -> list[dict]:
    """Scrape novel list from trxs.cc using headless browser.

    Returns [{"title": str, "author": str, "url": str, "category": str}, ...]
    """
    from playwright.sync_api import sync_playwright

    books = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Visit the tongren listing page
        page.goto("https://www.trxs.cc/tongren/", timeout=30000, wait_until="networkidle")
        time.sleep(2)

        # Get all novel links
        links = page.eval_on_selector_all(
            "a[href*='/tongren/']",
            "els => els.map(e => ({href: e.getAttribute('href'), text: e.textContent.trim()}))"
        )

        for link in links:
            href = link["href"]
            text = link["text"]
            # Skip category/index links, only keep actual novel pages
            if not text or len(text) < 2:
                continue
            if re.search(r'(index|tags|rating|search)', href):
                continue
            if not re.search(r'/tongren/\d+/', href):
                continue

            url = f"https://www.trxs.cc{href}" if href.startswith("/") else href
            if not any(b["url"] == url for b in books):
                books.append({
                    "title": text,
                    "author": "",
                    "url": url,
                    "category": "同人",
                })
            if len(books) >= max_books:
                break

        browser.close()

    print(f"[trxs] 发现 {len(books)} 本书")
    return books


def fetch_trxs_chapters(book_url: str, max_chapters: int = 40) -> list[dict]:
    """Get chapter list from a trxs.cc book page using headless browser.

    Returns [{"chapter_no": int, "title": str, "url": str}, ...]
    """
    from playwright.sync_api import sync_playwright

    chapters = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(book_url, timeout=30000, wait_until="networkidle")
        time.sleep(2)

        # Extract chapter links
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => ({href: e.getAttribute('href'), text: e.textContent.trim()}))"
        )

        seen = set()
        for link in links:
            href = link["href"]
            text = link["text"]
            if not text or not href:
                continue
            # Match chapter URLs: /tongren/XXXX/YYYY.html or similar
            if not re.search(r'/tongren/\d+/\d+\.html', href):
                continue
            if href in seen:
                continue
            seen.add(href)

            full_url = f"https://www.trxs.cc{href}" if href.startswith("/") else href
            # Extract chapter number from URL
            ch_match = re.search(r'/(\d+)\.html', href)
            ch_no = int(ch_match.group(1)) if ch_match else len(chapters) + 1

            chapters.append({
                "chapter_no": ch_no,
                "title": text,
                "url": full_url,
            })

        chapters.sort(key=lambda c: c["chapter_no"])

        browser.close()

    chapters = chapters[:max_chapters]
    print(f"[trxs] 从 {book_url} 发现 {len(chapters)} 章")
    return chapters


def fetch_trxs_content(chapter_url: str) -> Optional[str]:
    """Download and clean a trxs.cc chapter using headless browser.

    Returns cleaned text or None on failure.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(chapter_url, timeout=30000, wait_until="networkidle")
            time.sleep(1)

            # Get the page text, excluding scripts
            text = page.eval_on_selector_all(
                "body",
                "els => els[0].innerText"
            )

            # Clean up
            text = re.sub(r'document\.write.*', '', text)
            text = re.sub(r'function\s+\w+\([^)]*\).*', '', text)
            text = re.sub(r'if\s*\(.*?\).*', '', text)
            text = re.sub(r'var\s+\w+.*', '', text)
            text = re.sub(r'\n{3,}', '\n\n', text)

            browser.close()

            if len(text) > 200:
                return text.strip()
            return None

        except Exception as e:
            browser.close()
            print(f"[trxs] 章节下载失败 {chapter_url}: {e}")
            return None
