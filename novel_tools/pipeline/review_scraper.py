"""review_scraper — 评论抓取：豆瓣短评 + 贴吧帖子."""

import re
import time
import urllib.parse
from novel_tools.pipeline.db import add_review


def _get_session():
    import os
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Accept": "text/html,application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    # 通过环境变量支持代理（国内访问豆瓣等需要）
    for proto in ("HTTP", "HTTPS"):
        env_key = f"{proto}_PROXY"
        proxy = os.environ.get(env_key)
        if proxy:
            s.proxies[proto.lower()] = proxy
    return s


def scrape_douban_reviews(book_title: str, limit: int = 20) -> list[dict]:
    """
    从豆瓣搜索书籍并抓取短评。

    流程:
    1. 用书名搜索豆瓣: https://www.douban.com/search?cat=1001&q={title}
    2. 从搜索结果提取第一本书的 subject id
    3. 抓取短评: https://book.douban.com/subject/{id}/comments/
    4. 提取评论内容、评分、日期

    Returns: [{"content": str, "rating": int, "date": str}, ...]
    """
    session = _get_session()
    reviews = []

    # Step 1: Search for book
    search_url = f"https://www.douban.com/search?cat=1001&q={urllib.parse.quote(book_title)}"
    try:
        r = session.get(search_url, timeout=15)
        r.encoding = 'utf-8'
        html_text = r.text
        # 豆瓣搜索结果通过 /link2/?url=... 跳转，从 URL 编码中提取 subject ID
        subject_match = re.search(r'/link2/\?url=.*?subject%2F(\d+)%2F', html_text)
        if not subject_match:
            # 回退：直接搜索 subject/数字/
            subject_match = re.search(r'subject/(\d+)/', html_text)
        if not subject_match:
            print(f"[douban] 未找到书籍: {book_title}")
            return reviews
        subject_id = subject_match.group(1)
    except Exception as e:
        print(f"[douban] 搜索失败: {e}")
        return reviews

    # Step 2: Fetch reviews
    comments_url = f"https://book.douban.com/subject/{subject_id}/comments/"
    try:
        r = session.get(comments_url, timeout=15, headers={"Referer": search_url})
        r.encoding = 'utf-8'
        html = r.text

        # Extract comments: <span class="short">content</span>
        comment_pattern = re.compile(r'<span class="short">(.*?)</span>', re.DOTALL)
        rating_pattern = re.compile(r'class="allstar(\d+)', re.DOTALL)

        comments = comment_pattern.findall(html)
        ratings = rating_pattern.findall(html)

        for i, comment in enumerate(comments[:limit]):
            clean = re.sub(r'<[^>]+>', '', comment).strip()
            if len(clean) < 5:
                continue
            rating = int(ratings[i]) // 10 if i < len(ratings) else 0  # 40 -> 4
            reviews.append({"content": clean, "rating": rating, "source": "douban"})

    except Exception as e:
        print(f"[douban] 评论抓取失败: {e}")

    return reviews


def scrape_tieba_posts(book_title: str, limit: int = 20) -> list[dict]:
    """
    从百度贴吧抓取相关帖子。

    流程:
    1. 搜索贴吧: https://tieba.baidu.com/f?kw={title}
    2. 如果贴吧不存在，搜索帖子: https://tieba.baidu.com/f/search/res?qw={title}
    3. 提取帖子标题和内容摘要

    Returns: [{"content": str, "source": str}, ...]
    """
    session = _get_session()
    reviews = []

    # Try to access the tieba directly
    kw = urllib.parse.quote(book_title)
    tieba_url = f"https://tieba.baidu.com/f?kw={kw}"

    try:
        r = session.get(tieba_url, timeout=15)
        r.encoding = 'utf-8'
        html = r.text

        # Extract post titles and abstracts
        # Pattern: <a class="j_th_tit" href="/p/..." title="content">
        title_pattern = re.compile(r'<a[^>]*class="j_th_tit"[^>]*title="([^"]*)"', re.DOTALL)
        # Also get thread abstracts: <div class="threadlist_abs">content</div>
        abstract_pattern = re.compile(r'<div class="threadlist_abs[^"]*">(.*?)</div>', re.DOTALL)

        titles = title_pattern.findall(html)
        abstracts = abstract_pattern.findall(html)

        for i, title in enumerate(titles[:limit]):
            content = title.strip()
            if i < len(abstracts):
                abs_text = re.sub(r'<[^>]+>', '', abstracts[i]).strip()
                if abs_text:
                    content += " | " + abs_text[:100]
            if len(content) > 5:
                reviews.append({"content": content, "source": "tieba"})

    except Exception as e:
        print(f"[tieba] 抓取失败: {e}")

    return reviews


def scrape_reviews_for_book(book_id: int, book_title: str, sources: list[str] | None = None) -> dict:
    """
    为指定书籍抓取评论并存入数据库。

    Args:
        book_id: 数据库中的书籍 ID
        book_title: 书名（用于搜索）
        sources: 抓取来源列表，默认 ["douban", "tieba"]

    Returns: {"douban": N, "tieba": M, "total": N+M}
    """
    if sources is None:
        sources = ["douban", "tieba"]

    stats = {"douban": 0, "tieba": 0}

    if "douban" in sources:
        reviews = scrape_douban_reviews(book_title)
        for r in reviews:
            add_review(book_id, "douban", r["content"],
                      sentiment="negative" if r.get("rating", 3) <= 2 else "positive",
                      keywords="")
        stats["douban"] = len(reviews)
        time.sleep(1)

    if "tieba" in sources:
        reviews = scrape_tieba_posts(book_title)
        for r in reviews:
            add_review(book_id, "tieba", r["content"], sentiment="", keywords="")
        stats["tieba"] = len(reviews)

    stats["total"] = stats["douban"] + stats["tieba"]
    return stats
