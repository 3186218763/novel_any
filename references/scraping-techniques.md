# 网文抓取技术参考

## bqglll.cc

### 访问策略

- **手机版 (m.bqglll.cc)**: 首页和分类页可直接访问，但章节页被 Cloudflare JS Challenge 拦截
- **桌面版 (www.bqglll.cc)**: 书籍信息页可访问（含完整章节列表），章节页需特殊参数
- **关键发现**: 章节 URL 加 `?get=content` 参数可触发服务端渲染，绕过 JS Challenge，返回真实内容（但仅 ~1079 字预览）

### URL 模式

| 页面类型 | URL 格式 | 可访问 |
|---------|---------|--------|
| 首页 | `https://m.bqglll.cc/` | ✅ |
| 分类 | `https://m.bqglll.cc/{slug}/` | ✅ |
| 排行榜 | `https://m.bqglll.cc/top/` | ✅ |
| 书籍信息 | `https://www.bqglll.cc/look/{id}/` | ✅ (含 `listmain` 章节列表) |
| 章节内容 | `https://www.bqglll.cc/look/{id}/{ch}.html?get=content` | ✅ (预览) |
| 章节列表 | `https://m.bqglll.cc/look/{id}/list.html` | ❌ Cloudflare 拦截 |

### 章节列表提取

桌面版书籍页的章节列表在 `<div class="listmain">` > `<dl>` > `<dd>` 标签内：

```html
<dd><a href ="/look/9260/1.html">第一章 田园惊变</a></dd>
```

正则：
```python
r'<dd>\s*<a\s+href\s*=\s*"((?:/look/\d+/)?(\d+)\.html)"\s*>\s*([^<]+?)\s*</a>\s*</dd>'
```

注意：`href` 后有空格（`href ="/look/...`），不是标准 HTML。

### 内容提取

章节页用 `id="chaptercontent"` 容器，`?get=content` 参数触发服务端渲染。

## 多站点规则引擎

移植自 [owllook](https://github.com/howie6879/owllook) ⭐2841。每个站点配 3 元组：

```python
(章节列表选择器, 内容选择器, base_url类型)
```

示例：
```python
"bqglll.cc":  ({"class": "listmain"}, {"id": "chaptercontent"}, "same")
"biquge.com.cn": ({"id": "list"}, {"id": "content"}, "same")
"23qb.com": ({"id": "chapterList"}, {"id": "TextContent"}, "same")
```

已支持 9 个域名：bqglll.cc, biquge.com.cn, biquge.info, biqukan.com, bqg5200.com, 23qb.com, biqudu.com, biquge.tv, xbiquge.la。

## 豆瓣评论抓取

### 搜索

豆瓣搜索结果通过 `/link2/` 跳转，subject ID 被 URL 编码：

```
/link2/?url=https%3A%2F%2Fbook.douban.com%2Fsubject%2F3705820%2F
```

提取正则：
```python
r'/link2/\?url=.*?subject%2F(\d+)%2F'
```

### 评论页

```
https://book.douban.com/subject/{id}/comments/
```

评论内容：`<span class="short">content</span>`
评分：`class="allstar\d+"` (除以 10 得到 1-5 星)

### 代理

国内需代理访问豆瓣：
```bash
export HTTP_PROXY=http://127.0.0.1:10090
```

## 已知局限

- bqglll.cc 章节内容仅为预览片段（~1079 字），非完整章节
- 豆瓣对网文书名匹配率低（长书名、带符号的难匹配）
- 百度贴吧需 JS 渲染，requests 获取不完整
