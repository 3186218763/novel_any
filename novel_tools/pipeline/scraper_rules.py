"""pipeline.scraper_rules — Multi-site rules engine for biquge mirrors.

Inspired by owllook's approach to handling multiple biquge mirror sites.
Each site has selectors for chapter lists and content, plus a base URL resolution strategy.
"""

from urllib.parse import urlparse

# ── Site Rules ────────────────────────────────────────────────────────────
#
# Each entry maps a domain to:
#   chapter_list_selector : dict for BeautifulSoup.find() to locate the
#                           container holding chapter <a> links.
#   content_selector      : dict for BeautifulSoup.find() to locate the
#                           container holding chapter body text.
#   base_url_type         : 'same'      → reuse the request domain as base
#                           'noscheme'  → hrefs are relative paths, prepend domain
#                           'full_url'  → use a specific base URL string

SITE_RULES = {
    "bqglll.cc": {
        "chapter_list_selector": {"class": "listmain"},
        "content_selector": {"id": "chaptercontent"},
        "base_url_type": "same",
    },
    "biquge.com.cn": {
        "chapter_list_selector": {"id": "list"},
        "content_selector": {"id": "content"},
        "base_url_type": "same",
    },
    "biquge.info": {
        "chapter_list_selector": {"class": "box_con"},
        "content_selector": {"id": "content"},
        "base_url_type": "same",
    },
    "biqukan.com": {
        "chapter_list_selector": {"class": "listmain"},
        "content_selector": {"id": "content"},
        "base_url_type": "same",
    },
    "bqg5200.com": {
        "chapter_list_selector": {"id": "readerlist"},
        "content_selector": {"id": "content"},
        "base_url_type": "same",
    },
    "23qb.com": {
        "chapter_list_selector": {"id": "chapterList"},
        "content_selector": {"id": "TextContent"},
        "base_url_type": "same",
    },
    "biqudu.com": {
        "chapter_list_selector": {"class": "box_con"},
        "content_selector": {"id": "content"},
        "base_url_type": "same",
    },
    "biquge.tv": {
        "chapter_list_selector": {"class": "box_con"},
        "content_selector": {"id": "content"},
        "base_url_type": "same",
    },
    "xbiquge.la": {
        "chapter_list_selector": {"class": "box_con"},
        "content_selector": {"id": "content"},
        "base_url_type": "same",
    },
}


# ── Helper functions ──────────────────────────────────────────────────────


def _extract_domain(url: str) -> str:
    """Extract the bare domain (netloc) from a URL, stripping 'www.'/'m.' prefix."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    # Strip common mobile/desktop subdomain prefixes for matching
    for prefix in ("www.", "m.", "wap."):
        if netloc.startswith(prefix):
            netloc = netloc[len(prefix):]
            break
    return netloc


def get_rules_for_url(url: str) -> tuple | None:
    """Return (chapter_selector, content_selector, base_type) for a URL, or None.

    The returned selectors are dicts suitable for BeautifulSoup.find().
    base_type is one of 'same', 'noscheme', or a full URL string.
    """
    domain = _extract_domain(url)
    rules = SITE_RULES.get(domain)
    if rules is None:
        return None
    return (
        rules["chapter_list_selector"],
        rules["content_selector"],
        rules["base_url_type"],
    )


def list_supported_domains() -> list:
    """Return a sorted list of all supported domain strings."""
    return sorted(SITE_RULES.keys())
