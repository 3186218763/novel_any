"""pipeline.scraper — 多站点小说抓取工具.

支持 biquge 系列镜像站，通过 scraper_rules 规则引擎适配不同站点。

pip install cloudscraper beautifulsoup4 -q
"""

import html
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from . import db
from .scraper_rules import get_rules_for_url, list_supported_domains

BASE_URL = "https://m.bqglll.cc"
WWW_URL = "https://www.bqglll.cc"

DEFAULT_DOMAIN = "bqglll.cc"

CATEGORIES: dict[str, str] = {
    "玄幻": "xuanhuan",
    "武侠": "wuxia",
    "都市": "dushi",
    "历史": "lishi",
    "网游": "wangyou",
    "科幻": "kehuan",
    "女生": "mm",
}
CATEGORY_CN: dict[str, str] = {v: k for k, v in CATEGORIES.items()}

# 数据目录 — db.py 的 PIPELINE_DIR 是 .../novel_any/data/pipeline
PIPELINE_DIR = Path(__file__).parent.parent.parent / "data" / "pipeline"
BOOKS_DIR = PIPELINE_DIR / "books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)

# ── 导航文本清理 ─────────────────────────────────────
NAV_PATTERNS = [
    re.compile(r"请记住本书首发域名.*?，最快更新", re.DOTALL),
    re.compile(r"手机版阅读地址.*?", re.DOTALL),
    re.compile(r"最快更新.*?最新章节！", re.DOTALL),
    re.compile(r"笔趣阁.*?最快更新.*?无广告！", re.DOTALL),
    re.compile(r"m\\.bqglll\\.cc", re.DOTALL),
    re.compile(r"www\\.bqglll\\.cc", re.DOTALL),
    re.compile(r"一秒记住.*?：.*?。", re.DOTALL),
    re.compile(r"天才一秒记住.*?。", re.DOTALL),
]

# 章节内容优先搜索的容器 ID
CONTENT_IDS = ["chaptercontent", "content", "txt", "article", "nr1"]

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
        # 尝试桌面版作为回退
        print("[INFO] 移动版首页不可用，尝试桌面版...")
        html_text = _fetch(WWW_URL, session)
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


def fetch_category_books(category: str, page: int = 1, limit: int = 10) -> list[dict]:
    """从分类页面抓取书籍列表.

    Args:
        category: 分类标识，可以是中文名（如"玄幻"）或英文 slug（如"xuanhuan"）
        page: 页码（从 1 开始）
        limit: 最大返回数量

    Returns:
        [{"title": str, "author": str, "url": str, "category": str}, ...]
    """
    # 解析 category 名称：支持中文名或英文 slug
    slug = CATEGORIES.get(category, category)

    # 验证 slug 有效性
    if slug not in CATEGORY_CN:
        valid = ", ".join(f"{cn}({en})" for cn, en in CATEGORIES.items())
        print(f"[ERROR] 未知分类: {category}，可用: {valid}")
        return []

    cn_name = CATEGORY_CN[slug]
    url = f"{BASE_URL}/{slug}/"
    if page > 1:
        url = f"{BASE_URL}/{slug}/{page}.html"

    session = _get_session()
    html_text = _fetch(url, session)
    if not html_text:
        print(f"[ERROR] 无法访问分类页面: {url}")
        return []

    soup = BeautifulSoup(html_text, "lxml")

    # 分类页书籍列表在 <div class="block"> 下的链接
    # 结构: <a href="/look/NNN/">title</a> ... <span>author</span>
    books = []
    for block in soup.find_all("div", class_="block"):
        for a_tag in block.find_all("a", href=re.compile(r"^/look/\d+/")):
            title = a_tag.get_text(strip=True)
            if not title:
                continue
            path = a_tag["href"]
            book_url = BASE_URL + path

            # 尝试在同级或父级找作者 span
            author = ""
            parent = a_tag.parent
            if parent:
                span = parent.find("span")
                if span:
                    author = span.get_text(strip=True)
            if not author:
                # 在附近文本中搜索作者
                next_text = a_tag.next_sibling
                if next_text:
                    author = str(next_text).strip()

            # 去除纯数字/标签噪声
            if author and (author.isdigit() or len(author) < 2):
                author = ""

            if not any(b["url"] == book_url for b in books):
                books.append({
                    "title": title,
                    "author": author,
                    "url": book_url,
                    "category": cn_name,
                })
            if len(books) >= limit:
                break
        if len(books) >= limit:
            break

    print(f"[INFO] 从分类「{cn_name}」第 {page} 页发现 {len(books)} 本书")
    return books


def fetch_ranking_books(page: int = 1, limit: int = 10) -> list[dict]:
    """从排行榜页面抓取书籍列表.

    Args:
        page: 页码（从 1 开始）
        limit: 最大返回数量

    Returns:
        [{"title": str, "author": str, "url": str, "rank": int}, ...]
    """
    url = f"{BASE_URL}/top/"
    if page > 1:
        url = f"{BASE_URL}/top/{page}.html"

    session = _get_session()
    html_text = _fetch(url, session)
    if not html_text:
        # 尝试 www 版
        www_top = f"{WWW_URL}/top/"
        if page > 1:
            www_top = f"{WWW_URL}/top/{page}.html"
        print("[INFO] 移动版排行不可用，尝试桌面版...")
        html_text = _fetch(www_top, session)
    if not html_text:
        print("[ERROR] 无法访问排行榜页面")
        return []

    soup = BeautifulSoup(html_text, "lxml")

    # 排行页结构：<div class="block"> 内含排行列表
    # 每项可能是 <a href="/look/NNN/">title</a> + <span>author</span>
    books = []
    rank = (page - 1) * 20  # 估算排名起始位置

    for block in soup.find_all("div", class_="block"):
        for a_tag in block.find_all("a", href=re.compile(r"^/look/\d+/")):
            title = a_tag.get_text(strip=True)
            if not title:
                continue
            path = a_tag["href"]
            book_url = BASE_URL + path

            author = ""
            parent = a_tag.parent
            if parent:
                span = parent.find("span")
                if span:
                    author = span.get_text(strip=True)

            rank += 1
            if not any(b["url"] == book_url for b in books):
                books.append({
                    "title": title,
                    "author": author,
                    "url": book_url,
                    "rank": rank,
                })
            if len(books) >= limit:
                break
        if len(books) >= limit:
            break

    print(f"[INFO] 从排行榜第 {page} 页发现 {len(books)} 本书")
    return books


def fetch_book_chapters(book_url: str, max_chapters: int = 50) -> list[dict]:
    """从书籍目录页获取章节列表（使用 www 版避免 Cloudflare 拦截）.

    Returns:
        [{"chapter_no": int, "title": str, "url": str}, ...]
    """
    session = _get_session()
    # 将 m.bqglll.cc 转为 www.bqglll.cc（桌面版有完整章节列表）
    www_url = book_url.replace("m.bqglll.cc", "www.bqglll.cc")
    html_text = _fetch(www_url, session)
    if not html_text:
        print(f"[ERROR] 无法访问书籍页面: {www_url}")
        return []

    # www 版章节在 <div class="listmain"> > <dl> > <dd><a href ="/look/NNN/MMMM.html">标题</a></dd>
    # href 后面有空格: href ="/look/..."
    chapter_pattern = re.compile(
        r'<dd>\s*<a\s+href\s*=\s*"((?:/look/\d+/)?(\d+)\.html)"\s*>\s*([^<]+?)\s*</a>\s*</dd>',
        re.DOTALL,
    )

    chapters = []
    seen = set()
    for match in chapter_pattern.finditer(html_text):
        path = match.group(1)
        chapter_no = int(match.group(2))
        title = match.group(3).strip()
        if chapter_no in seen:
            continue
        seen.add(chapter_no)
        # 补全路径
        if not path.startswith("/look/"):
            # 提取 book id 从 www_url
            book_id_match = re.search(r"/look/(\d+)/", www_url)
            if book_id_match:
                path = f"/look/{book_id_match.group(1)}/{path}"
        url = WWW_URL + path
        chapters.append({"chapter_no": chapter_no, "title": title, "url": url})

    chapters.sort(key=lambda c: c["chapter_no"])
    chapters = chapters[:max_chapters]
    print(f"[INFO] 从 {www_url} 发现 {len(chapters)} 章")
    return chapters


def fetch_chapter_content(chapter_url: str) -> str:
    """下载并清洗单章内容（使用 www 版 + ?get=content 参数绕过 Cloudflare）."""
    session = _get_session()
    www_url = chapter_url.replace("m.bqglll.cc", "www.bqglll.cc")
    # 添加 ?get=content 参数触发服务端渲染内容
    if "?" not in www_url:
        www_url += "?get=content"
    html_text = _fetch(www_url, session)
    if not html_text:
        return ""
    return _clean_chapter_content(html_text)


# ── 主流程 ───────────────────────────────────────────

def discover_and_fetch(
    limit: int = 3,
    max_chapters: int = 50,
    discovery_mode: str = "homepage",
) -> dict:
    """主流程：发现书籍 → 抓取章节 → 保存到 DB 和文件系统.

    1. 根据 discovery_mode 发现 `limit` 本书
    2. 每本书获取最多 `max_chapters` 章
    3. 章节保存到 data/pipeline/books/{book_id}/ch{no:03d}.md
    4. 0 章下载的书籍自动标记为 deprecated

    Args:
        limit: 最大发现书籍数量
        max_chapters: 每本书最大下载章数
        discovery_mode: 发现模式 -
            "homepage" (默认): 从首页发现
            "ranking": 从排行榜发现
            "category:玄幻": 从指定分类发现（如 "category:玄幻", "category:xuanhuan"）
            "all": 综合所有方式，去重后返回

    Returns:
        {"books_added": int, "chapters_downloaded": int, "errors": list}
    """
    stats: dict = {"books_added": 0, "chapters_downloaded": 0, "errors": []}

    # ── 1. 根据模式发现书籍 ──
    mode = discovery_mode.strip().lower()
    books: list[dict] = []
    seen_urls: set[str] = set()

    def _deduplicate_candidates(candidates: list[dict]) -> list[dict]:
        """按 url 去重，保持顺序."""
        result = []
        for b in candidates:
            if b["url"] not in seen_urls:
                seen_urls.add(b["url"])
                result.append(b)
        return result

    if mode == "ranking":
        books = fetch_ranking_books(limit=limit)
    elif mode.startswith("category:"):
        cat = discovery_mode[len("category:"):].strip()
        books = fetch_category_books(cat, limit=limit)
    elif mode == "all":
        # 综合所有方式
        from_sources: list[list[dict]] = [
            fetch_homepage_books(limit=limit),
            fetch_ranking_books(limit=limit),
        ]
        for cat_slug in CATEGORIES.values():
            from_sources.append(fetch_category_books(cat_slug, limit=max(2, limit // 2)))
        for source_books in from_sources:
            books.extend(_deduplicate_candidates(source_books))
        books = books[:limit]
        print(f"[INFO] 综合发现模式: 去重后共 {len(books)} 本书")
    else:
        # 默认 homepage
        books = fetch_homepage_books(limit=limit)

    if not books:
        stats["errors"].append(f"未发现任何书籍 (模式: {mode})")
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
