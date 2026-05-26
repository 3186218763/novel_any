"""pipeline.scraper — bqglll.cc 小说抓取工具.

pip install cloudscraper beautifulsoup4 -q
"""

import html
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from . import db

BASE_URL = "https://m.bqglll.cc"

# 数据目录 — db.py 的 PIPELINE_DIR 是 .../novel_any/data/pipeline
PIPELINE_DIR = Path(__file__).parent.parent.parent / "data" / "pipeline"
BOOKS_DIR = PIPELINE_DIR / "books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)

# ── 导航文本清理 ─────────────────────────────────────
NAV_PATTERNS = [
    re.compile(r"请记住本书首发域名.*?", re.DOTALL),
    re.compile(r"手机版阅读地址.*?", re.DOTALL),
    re.compile(r"最快更新.*?", re.DOTALL),
    re.compile(r"笔趣阁.*?最快更新.*?", re.DOTALL),
    re.compile(r"m\.bqglll\.cc", re.DOTALL),
]

# 章节内容优先搜索的容器 ID
CONTENT_IDS = ["content", "chaptercontent", "txt", "article", "nr1"]

# ── 会话 ─────────────────────────────────────────────

def _get_session():
    """创建 HTTP 会话，优先使用 cloudscraper，回退到 requests.Session."""
    try:
        import cloudscraper

        return cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    except ImportError:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Mobile Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )
        return session


# ── HTTP 工具 ────────────────────────────────────────

def _fetch(url: str, session=None) -> str | None:
    """安全 GET 请求，返回响应文本或 None."""
    sess = session or _get_session()
    try:
        resp = sess.get(url, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except Exception as exc:
        print(f"  [WARN] 请求失败 {url}: {exc}")
        return None


# ── 内容清洗 ─────────────────────────────────────────

def _clean_chapter_content(html_text: str) -> str:
    """从 HTML 中提取并清洗章节正文."""
    soup = BeautifulSoup(html_text, "lxml")

    # 移除 script / style 等标签
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    # 尝试从已知容器提取正文
    content_div = None
    for cid in CONTENT_IDS:
        content_div = soup.find(id=cid)
        if content_div:
            break

    if content_div is None:
        content_div = soup.body or soup

    # 提取纯文本
    text = content_div.get_text(separator="\n", strip=True)

    # 解码 HTML 实体
    text = html.unescape(text)

    # 移除导航 / 广告文本
    for pat in NAV_PATTERNS:
        text = pat.sub("", text)

    # 压缩多余空行
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


# ── 公共抓取 API ────────────────────────────────────

def fetch_homepage_books(limit: int = 10) -> list[dict]:
    """从 bqglll.cc 首页抓取书籍列表.

    Returns:
        [{"title": str, "author": str, "url": str}, ...]
    """
    session = _get_session()
    html_text = _fetch(BASE_URL, session)
    if not html_text:
        print("[ERROR] 无法访问首页")
        return []

    book_pattern = re.compile(
        r'<a href="(/look/\d+/)"[^>]*>([^<]+)</a>.*?<span[^>]*>([^<]+)</span>',
        re.DOTALL,
    )

    books = []
    for match in book_pattern.finditer(html_text):
        path = match.group(1)
        title = match.group(2).strip()
        author = match.group(3).strip()
        url = BASE_URL + path
        # 按 url 去重
        if not any(b["url"] == url for b in books):
            books.append({"title": title, "author": author, "url": url})
        if len(books) >= limit:
            break

    print(f"[INFO] 从首页发现 {len(books)} 本书")
    return books


def fetch_book_chapters(book_url: str, max_chapters: int = 50) -> list[dict]:
    """从书籍目录页获取章节列表.

    Returns:
        [{"chapter_no": int, "title": str, "url": str}, ...]
    """
    session = _get_session()
    html_text = _fetch(book_url, session)
    if not html_text:
        print(f"[ERROR] 无法访问书籍页面: {book_url}")
        return []

    chapter_pattern = re.compile(
        r'<a\s+href="(/look/\d+/(\d+)\.html)"[^>]*>([^<]+)</a>',
        re.DOTALL,
    )

    chapters = []
    for match in chapter_pattern.finditer(html_text):
        path = match.group(1)
        chapter_no = int(match.group(2))
        title = match.group(3).strip()
        url = BASE_URL + path
        chapters.append({"chapter_no": chapter_no, "title": title, "url": url})
        if len(chapters) >= max_chapters:
            break

    chapters.sort(key=lambda c: c["chapter_no"])
    print(f"[INFO] 从 {book_url} 发现 {len(chapters)} 章")
    return chapters


def fetch_chapter_content(chapter_url: str) -> str:
    """下载并清洗单章内容."""
    session = _get_session()
    html_text = _fetch(chapter_url, session)
    if not html_text:
        return ""
    return _clean_chapter_content(html_text)


# ── 主流程 ───────────────────────────────────────────

def discover_and_fetch(limit: int = 3, max_chapters: int = 50) -> dict:
    """主流程：发现书籍 → 抓取章节 → 保存到 DB 和文件系统.

    1. 从首页发现 `limit` 本书
    2. 每本书获取最多 `max_chapters` 章
    3. 章节保存到 data/pipeline/books/{book_id}/ch{no:03d}.md
    4. 0 章下载的书籍自动标记为 deprecated

    Returns:
        {"books_added": int, "chapters_downloaded": int, "errors": list}
    """
    stats: dict = {"books_added": 0, "chapters_downloaded": 0, "errors": []}

    # ── 1. 发现书籍 ──
    books = fetch_homepage_books(limit=limit)
    if not books:
        stats["errors"].append("未发现任何书籍")
        return stats

    for book in books:
        try:
            print(f"\n{'=' * 50}")
            print(f"[BOOK] {book['title']} — {book['author']}")

            # 注册到 DB
            book_id = db.add_book(
                title=book["title"],
                author=book["author"],
                source_url=book["url"],
                category="",
            )
            stats["books_added"] += 1

            book_dir = BOOKS_DIR / str(book_id)
            book_dir.mkdir(parents=True, exist_ok=True)

            # ── 2. 获取章节列表 ──
            chapters = fetch_book_chapters(book["url"], max_chapters=max_chapters)
            if not chapters:
                print(f"  [DEPR] 无章节，标记为 deprecated")
                db.mark_book_status(book_id, "deprecated")
                stats["errors"].append(f"无章节: {book['title']}")
                continue

            # ── 3. 下载章节 ──
            chapter_count = 0
            for ch in chapters:
                try:
                    print(f"  [CH] {ch['chapter_no']:03d} {ch['title']}", end=" ")

                    content = fetch_chapter_content(ch["url"])
                    if not content:
                        print("(空)")
                        time.sleep(0.5)  # 失败后等待更长时间
                        continue

                    # 写入文件
                    file_path = book_dir / f"ch{ch['chapter_no']:03d}.md"
                    file_path.write_text(content, encoding="utf-8")

                    word_count = len(content)

                    # 写入 DB
                    db.add_chapter(
                        book_id=book_id,
                        chapter_no=ch["chapter_no"],
                        title=ch["title"],
                        file_path=str(file_path),
                        word_count=word_count,
                    )

                    chapter_count += 1
                    stats["chapters_downloaded"] += 1
                    print(f"({word_count} 字)")

                    time.sleep(0.3)  # 速率限制

                except Exception as exc:
                    print(f"(失败: {exc})")
                    stats["errors"].append(
                        f"章节下载失败: {ch['title']}: {exc}"
                    )
                    time.sleep(0.5)

            # 0 章下载 → 标记 deprecated
            if chapter_count == 0:
                print(f"  [DEPR] 0 章下载，标记为 deprecated")
                db.mark_book_status(book_id, "deprecated")
            else:
                print(f"  [OK] 下载 {chapter_count} 章")

        except Exception as exc:
            print(f"  [ERROR] 处理书籍失败: {exc}")
            stats["errors"].append(f"书籍处理失败: {book['title']}: {exc}")
            time.sleep(0.5)

    print(f"\n{'=' * 50}")
    print(
        f"[DONE] 添加 {stats['books_added']} 本书, "
        f"下载 {stats['chapters_downloaded']} 章, "
        f"{len(stats['errors'])} 个错误"
    )
    return stats
