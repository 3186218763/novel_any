# biquge 站点抓取技术

bqglll.cc 及同类笔趣阁镜像的抓取方法、反爬应对和架构决策。

## bqglll.cc 反爬模式

### 移动端 vs 桌面端

- **移动端** (`m.bqglll.cc`): 章节页被 Cloudflare JS Challenge 拦截，返回 1731 字节 "加载中……" 页面
- **桌面端** (`www.bqglll.cc`): 书页可正常访问(~455KB)，包含完整章节列表
- **章节列表格式**: `<div class="listmain"> > <dl> > <dd><a href ="/look/NNN/MMMM.html">标题</a></dd>`
  - `href` 后可能有空格: `href ="/look/..."`
  - 正则: `r'<dd>\s*<a\s+href\s*=\s*"((?:/look/\d+/)?(\d+)\.html)"\s*>\s*([^<]+?)\s*</a>\s*</dd>'`

### ?get=content 参数

桌面版章节页默认也返回 "加载中……"。追加 URL 参数 `?get=content` 触发服务端渲染：

```
https://www.bqglll.cc/look/9260/2.html?get=content
```

返回内容在 `id="chaptercontent"` div 中。

**限制**: 返回的是预览片段(~1079 个中文字符)，非完整章节。所有参数变体(?get=full, ?page=all, ?v=2, ?format=txt)返回长度一致。

### 首页书籍发现

首页用正则提取:
```python
r'<a href="(/look/\d+/)"[^>]*>([^<]+)</a>.*?<span[^>]*>([^<]+)</span>'
```

### 分类页

移动版分类页(`/xuanhuan/`、`/dushi/` 等)可用:
```python
r'<a\s+href="(/look/\d+/)"[^>]*>([^<]+)</a>'
```

**不要用 BeautifulSoup 选择器** (`div.block`、`soup.find_all` 等) — 移动版 DOM 结构与桌面版不同。

## 镜像站生态

从 owllook 项目移植的 9 域名规则引擎（`pipeline/scraper_rules.py`）：

| 域名 | 状态 | 说明 |
|------|------|------|
| bqglll.cc | ✅ 可用 | ?get=content 预览片段 |
| biquge.com.cn | ❌ SSL 错误 | 证书不匹配 |
| biquge.info | ❌ Cloudflare | EOF SSL |
| biqukan.com | ❌ 403 | 直接禁止 |
| bqg5200.com | ❌ Cloudflare | EOF SSL |
| 23qb.com | ❌ Cloudflare | 403 |
| biqudu.com | ❌ Cloudflare | EOF SSL |
| biquge.tv | ❌ 空页面 | 无书籍链接 |
| xbiquge.la | ❌ Cloudflare | EOF SSL |

**结论**: 所有镜像站要么被 Cloudflare 保护，要么只返回预览片段。获取完整章节需用 headless browser (playwright/selenium) 或付费源。

## 排行榜陷阱

bqglll.cc `/top/` 排行榜前列返回成人向内容。数据采集优先用:
1. 首页推荐 (内容质量相对高)
2. 分类页 (可按类型筛选)
3. 排行榜 (仅作补充，需过滤)

## 章节内容清洗

```python
CONTENT_IDS = ["chaptercontent", "content", "txt", "article", "nr1"]
NAV_PATTERNS = [
    r"请记住本书首发域名.*?，最快更新",
    r"手机版阅读地址.*?",
    r"最快更新.*?最新章节！",
    r"笔趣阁.*?最快更新.*?无广告！",
    r"一秒记住.*?：.*?。",
    r"天才一秒记住.*?。",
]
```
