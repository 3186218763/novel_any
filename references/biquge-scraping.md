# bqglll.cc 抓取技术参考

> 日期: 2026-05-26
> 版本: v0.3.0 pipeline scraper

## URL 策略

| 页面类型 | 域名 | 备注 |
|---------|------|------|
| 首页 / 排行榜 | `m.bqglll.cc` 可用, `www` 也可用 | 两者都返回完整 HTML |
| 书籍信息页 + 章节列表 | **必须 `www`** | 移动版章节列表被 JS 渲染 |
| 章节内容页 | **必须 `www` + `?get=content`** | 否则返回 "加载中……" (1731 bytes) |

## 章节列表提取

www 版书籍页 (`/look/{book_id}/`) 的章节在 `<div class="listmain"> > <dl> > <dd>` 中：

```html
<div class="listmain">
    <dl>
        <dt>九星霸体诀最新章节列表</dt>
        <dd><a href ="/look/9260/1.html">感谢大家的关心</a></dd>
        <dd><a href ="/look/9260/2.html">第一章 田园惊变</a></dd>
        ...
    </dl>
</div>
```

正则模式（注意 `href` 后可能有空格）：
```python
chapter_pattern = re.compile(
    r'<dd>\s*<a\s+href\s*=\s*"((?:/look/\d+/)?(\d+)\.html)"\s*>\s*([^<]+?)\s*</a>\s*</dd>',
    re.DOTALL,
)
```

按 `chapter_no` 去重并排序。最多取 `max_chapters` 章。

## 章节内容提取

www 版章节页 (`/look/{book_id}/{ch_no}.html`) 默认返回 JS 加载骨架（1731 bytes，"加载中……"）。追加 `?get=content` 触发服务端渲染完整内容：

```
https://www.bqglll.cc/look/9260/2.html?get=content  → 7248+ bytes, 含真实正文
```

正文在 `<div id="chaptercontent">` 中。其他可能的容器 ID（按优先级）：`chaptercontent`, `content`, `txt`, `article`, `nr1`。

## 绕过 Cloudflare

- 移动端 (`m.bqglll.cc`) 章节页被 Cloudflare JS Challenge 完全拦截，即使 `cloudscraper` 和 `curl_cffi` 也无法绕过
- 桌面版 (`www.bqglll.cc`) 可通过 `cloudscraper` + `?get=content` 正常获取内容
- `cloudscraper` 配置：`browser={'browser':'chrome','platform':'windows','mobile':False}`
- 备用 `requests.Session` 需要设置移动端 User-Agent（Android Chrome）

## 内容清洗

BeautifulSoup + lxml 解析。清洗步骤：
1. 移除 `<script>`, `<style>`, `<noscript>`, `<iframe>` 标签
2. 从已知容器 ID 提取正文（`chaptercontent` 优先）
3. 解码 HTML 实体（`html.unescape`）
4. 移除导航/广告文本（正则匹配 "请记住本书首发域名…"、"笔趣阁…"、"一秒记住…" 等）
5. 压缩多余空行

## 速率限制

- 章节间间隔：0.3 秒
- 失败后间隔：0.5 秒
- 单书连续 5 章失败 → 跳过该书剩余章节
- 0 章下载 → 标记书籍为 `deprecated`

## 已知限制

- `?get=content` 返回的内容有时是预览/摘录（~1079 字），非完整章节
- 作者名在首页推荐列表中可能与实际不一致（如"九星霸体诀"作者显示为"唐家三少"而非"平凡魔术师"）
- 分类提取不完整（首页不区分玄幻/仙侠等子类）
