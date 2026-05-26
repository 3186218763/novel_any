# GitHub 爬虫项目调研

> 日期: 2026-05-26
> 用途: novel_auto_pipeline 的章节抓取、评论爬取、书籍发现三个方向的技术选型参考

## 1. 章节内容爬取

### howie6879/owllook ⭐2841 (Python, Apache-2.0)
- **核心借鉴对象**
- 小说搜索引擎，内含 ~100 个笔趣阁镜像站的 HTML 规则库
- 规则格式: `Rules(content_url, chapter_selector, content_selector)`
  - `chapter_selector`: CSS 选择器定位章节列表 (如 `{'class': 'box_con'}`, `{'id': 'list'}`)
  - `content_selector`: CSS 选择器定位正文容器 (如 `{'id': 'content'}`, `{'class': 'txtc'}`)
  - `content_url`: '0'=需拼接, '1'=直接使用, 或完整 base URL
- 支持搜索引擎发现（百度/360/bing/duckduckgo）
- asyncio/aiohttp 并发抓取
- 关键文件: `owllook/config/rules.py` (670 行规则配置)

### ma6254/FictionDown ⭐952 (Go, GPL-3.0)
- 小说下载器，支持起点+笔趣阁
- 导出格式: Markdown/TXT/EPUB
- 广告过滤 + 自动校对
- 不适合直接集成（Go 语言），架构思路可参考

### Mereithhh/NovelSpider ⭐4 (Python, Scrapy)
- 基于 Scrapy 的 biquge 爬虫
- 搜索功能: `biquge.com.cn/search.php?q=书名`
- 章节列表: `#list dl dd a` → 章节链接
- 正文提取: `#content` div → 纯文本
- 简单清晰，适合参考标准 biquge HTML 结构

### asan1148/QidianSpider ⭐2 (Python, Scrapy)
- 起点全站免费书列表采集
- 入口: `qidian.com/all` → 分页遍历
- 展示起点排行榜分页采集模式

## 2. 评论爬取

GitHub 上没有成熟的"中文网文评论爬虫"。推荐自建，按优先级：

**1. 豆瓣短评（最简单）** — `book.douban.com/subject/{id}/comments/`，反爬较弱
**2. 贴吧帖子（中等）** — `tieba.baidu.com/f?kw=书名`，HTML 结构简单
**3. 起点本章说（最复杂）** — 需登录态，API 需逆向，不推荐首选

## 3. 书籍发现

- bqglll.cc `/top/`（排行榜）+ `/xuanhuan/` 等分类页
- 在现有 scraper.py 中添加 `fetch_ranking_books(category, page)` 方法

## 4. 实施建议

| 功能 | 借用来源 | 复杂度 |
|------|---------|--------|
| 章节内容 | owllook 的 `rules.py` 规则引擎 | 中 |
| 评论抓取 | 自建豆瓣 + 贴吧解析 | 低 |
| 书籍发现 | bqglll.cc `/top/` + 分类页 | 低 |
