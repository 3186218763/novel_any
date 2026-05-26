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
from .scraper_rules import get_rules_for_url, list_supported_domains, SITE_RULES

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

def _clean_chapter_content(html_text: str, content_selector: dict | None = None) -> str:
    """从 HTML 中提取并清洗章节正文.

    Args:
        html_text: 原始 HTML 文本
        content_selector: BeautifulSoup.find() 用的属性字典，如 {'id': 'content'}
                          若为 None 则回退到 CONTENT_IDS 列表尝试
    """
    soup = BeautifulSoup(html_text, "lxml")

    # 移除 script / style 等标签
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    # 优先使用规则引擎指定的选择器
    content_div = None
    if content_selector:
        content_div = soup.find(**content_selector)

    # 规则选择器未命中则回退到已知 ID 列表
    if content_div is None:
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

def fetch_homepage_books(limit: int = 10, domain: str | None = None) -> list[dict]:
    """从小说站点首页抓取书籍列表.

    Args:
        limit: 最大返回数量
        domain: 目标域名（如 'bqglll.cc', 'biquge.com.cn'）。
                若为 None 则使用默认的 bqglll.cc

    Returns:
        [{"title": str, "author": str, "url": str}, ...]
    """
    target_domain = domain or DEFAULT_DOMAIN

    session = _get_session()

    # 构建首页 URL
    if target_domain == DEFAULT_DOMAIN:
        base = BASE_URL
        www = WWW_URL
        html_text = _fetch(base, session)
        if not html_text:
            print("[INFO] 移动版首页不可用，尝试桌面版...")
            html_text = _fetch(www, session)
    else:
        base = f"https://m.{target_domain}"
        www = f"https://www.{target_domain}"
        # 先尝试移动版
        html_text = _fetch(base, session)
        if not html_text:
            html_text = _fetch(www, session)
        # 如果 m/www 都失败，尝试裸域名
        if not html_text:
            bare = f"https://{target_domain}"
            html_text = _fetch(bare, session)
            if html_text:
                base = bare

    if not html_text:
        print("[ERROR] 无法访问首页")
        return []

    # bqglll.cc 专用 regex（不适用于其他站点）
    if target_domain == DEFAULT_DOMAIN:
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
            if not any(b["url"] == url for b in books):
                books.append({"title": title, "author": author, "url": url})
            if len(books) >= limit:
                break
    else:
        # 通用解析：使用 BeautifulSoup 提取链接和文本
        soup = BeautifulSoup(html_text, "lxml")
        books = []
        seen_urls = set()

        # 查找所有书籍链接（常见模式：<a> 包含书名，附近有作者 <span>）
        for a_tag in soup.find_all("a", href=True):
            title = a_tag.get_text(strip=True)
            href = a_tag["href"].strip()
            if not title or len(title) < 2 or href == "#":
                continue
            # 跳过导航链接
            skip = ("首页", "排行", "分类", "搜索", "关于", "登录", "注册",
                    "更多", "全部", "书库", "书架")
            if any(title == s for s in skip):
                continue
            full_url = urljoin(base, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # 尝试找作者
            author = ""
            parent = a_tag.parent
            if parent:
                span = parent.find("span")
                if span:
                    author = span.get_text(strip=True)

            books.append({"title": title, "author": author, "url": full_url})
            if len(books) >= limit:
                break

    print(f"[INFO] 从 {target_domain} 首页发现 {len(books)} 本书")
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
    """从书籍目录页获取章节列表.

    使用规则引擎适配不同站点。若站点不支持则回退到 bqglll.cc 的 regex 方式。

    Returns:
        [{"chapter_no": int, "title": str, "url": str}, ...]
    """
    session = _get_session()
    rules = get_rules_for_url(book_url)

    # 提取 base URL 用于拼接相对路径
    parsed = urlparse(book_url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"

    html_text = _fetch(book_url, session)
    if not html_text:
        print(f"[ERROR] 无法访问书籍页面: {book_url}")
        return []

    # ── 规则引擎路径：使用 BeautifulSoup + 选择器 ──
    if rules:
        ch_sel, _, _ = rules
        soup = BeautifulSoup(html_text, "lxml")
        container = soup.find(**ch_sel)
        chapters: list[dict] = []
        seen: set[str] = set()

        if container:
            # 查找容器内所有 <a> 链接（通常在 <dd><a> 中）
            for a_tag in container.find_all("a", href=True):
                href = a_tag["href"].strip()
                title = a_tag.get_text(strip=True)
                if not title or not href or href == "#":
                    continue
                # 跳过明显的非章节链接（如分页、首页等）
                skip_texts = ("首页", "上一页", "下一页", "末页", "返回", "目录",
                              "next", "prev", "home", ">>", "<<")
                if any(s in title for s in skip_texts):
                    continue
                # 解析完整 URL
                chapter_url = urljoin(book_url, href)
                if chapter_url in seen:
                    continue
                seen.add(chapter_url)
                chapter_no = len(chapters) + 1
                chapters.append({
                    "chapter_no": chapter_no,
                    "title": title,
                    "url": chapter_url,
                })

        chapters = chapters[:max_chapters]
        print(f"[INFO] 从 {book_url} 发现 {len(chapters)} 章 (规则引擎)")
        return chapters

    # ── 回退：bqglll.cc 专用 regex ──
    www_url = book_url.replace("m.bqglll.cc", "www.bqglll.cc")
    if www_url != book_url:
        html_text = _fetch(www_url, session)
        if not html_text:
            print(f"[ERROR] 无法访问书籍页面: {www_url}")
            return []
        book_url = www_url

    chapter_pattern = re.compile(
        r'<dd>\s*<a\s+href\s*=\s*"((?:/look/\d+/)?(\d+)\.html)"\s*>\s*([^<]+?)\s*</a>\s*</dd>',
        re.DOTALL,
    )

    chapters = []
    seen_nums = set()
    for match in chapter_pattern.finditer(html_text):
        path = match.group(1)
        chapter_no = int(match.group(2))
        title = match.group(3).strip()
        if chapter_no in seen_nums:
            continue
        seen_nums.add(chapter_no)
        if not path.startswith("/look/"):
            book_id_match = re.search(r"/look/(\d+)/", book_url)
            if book_id_match:
                path = f"/look/{book_id_match.group(1)}/{path}"
        url = WWW_URL + path
        chapters.append({"chapter_no": chapter_no, "title": title, "url": url})

    chapters.sort(key=lambda c: c["chapter_no"])
    chapters = chapters[:max_chapters]
    print(f"[INFO] 从 {book_url} 发现 {len(chapters)} 章 (regex 回退)")
    return chapters


def fetch_chapter_content(chapter_url: str) -> str:
    """下载并清洗单章内容.

    使用规则引擎适配不同站点的内容选择器。
    """
    session = _get_session()
    rules = get_rules_for_url(chapter_url)

    # 获取内容选择器（若站点有规则）
    content_selector = None
    if rules:
        _, content_selector, _ = rules

    # bqglll.cc 特殊处理：使用 www 版 + ?get=content 参数
    if "bqglll.cc" in chapter_url:
        www_url = chapter_url.replace("m.bqglll.cc", "www.bqglll.cc")
        if "?" not in www_url:
            www_url += "?get=content"
        html_text = _fetch(www_url, session)
    else:
        html_text = _fetch(chapter_url, session)

    if not html_text:
        return ""
    return _clean_chapter_content(html_text, content_selector=content_selector)


def fetch_book_from_domain(title: str, author: str, domain: str) -> dict | None:
    """在指定域名上搜索书籍，返回书籍信息或 None.

    尝试通过搜索或首页发现有匹配标题+作者的书籍。

    Args:
        title: 书名
        author: 作者名
        domain: 目标域名（如 'biquge.com.cn'）

    Returns:
        {"title": str, "author": str, "url": str} 或 None
    """
    if domain not in SITE_RULES:
        print(f"[ERROR] 不支持的域名: {domain}")
        print(f"  支持的域名: {', '.join(list_supported_domains())}")
        return None

    session = _get_session()

    # 尝试搜索：常见搜索 URL 模式
    search_urls = [
        f"https://{domain}/search.html?keyword={title}",
        f"https://www.{domain}/search.html?keyword={title}",
        f"https://{domain}/s?q={title}",
        f"https://www.{domain}/s?q={title}",
        f"https://{domain}/search/?keyword={title}",
    ]

    for search_url in search_urls:
        html_text = _fetch(search_url, session)
        if not html_text:
            continue

        soup = BeautifulSoup(html_text, "lxml")
        # 查找搜索结果中的书籍链接
        for a_tag in soup.find_all("a", href=True):
            link_title = a_tag.get_text(strip=True)
            if title in link_title:
                href = a_tag["href"].strip()
                book_url = urljoin(search_url, href)
                # 尝试找作者
                book_author = ""
                parent = a_tag.parent
                if parent:
                    span = parent.find("span")
                    if span:
                        book_author = span.get_text(strip=True)
                # 作者匹配（宽松）
                if not author or not book_author or author in book_author or book_author in author:
                    print(f"[INFO] 在 {domain} 搜索找到: {link_title}")
                    return {"title": link_title, "author": book_author, "url": book_url}
        print(f"  [INFO] 搜索 {search_url} 未找到匹配结果")

    # 回退：从首页找
    print(f"  [INFO] 搜索未果，尝试从 {domain} 首页查找...")
    books = fetch_homepage_books(limit=50, domain=domain)
    for book in books:
        if title in book["title"] and (not author or author in book.get("author", "")):
            print(f"[INFO] 在 {domain} 首页找到: {book['title']}")
            return book

    print(f"[WARN] 在 {domain} 未找到匹配的书籍: {title}")
    return None


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
