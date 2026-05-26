# 豆瓣评论抓取技术参考

> 日期: 2026-05-26
> 模块: novel_tools.pipeline.review_scraper

## 代理要求

豆瓣在国内网络环境中 DNS 被污染，直接访问会 SSL 错误。必须通过代理：

```python
import os
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:10090'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:10090'
```

`_get_session()` 会自动读取环境变量并设置 `session.proxies`。

## 搜索与 Subject ID 提取

豆瓣搜索结果不再直接暴露 `subject/{id}/` 链接。当前页面通过 `/link2/?url=...` 跳转，subject ID 被 URL-encoded：

```html
<a href="/link2/?url=https%3A%2F%2Fbook.douban.com%2Fsubject%2F3705820%2F&query=...">
```

提取正则（优先匹配 URL-encoded 格式，回退到明文）：

```python
subject_match = re.search(r'/link2/\?url=.*?subject%2F(\d+)%2F', html_text)
if not subject_match:
    subject_match = re.search(r'subject/(\d+)/', html_text)
```

## 评论抓取

获取 subject ID 后，评论页 URL: `https://book.douban.com/subject/{subject_id}/comments/`

评论内容在 `<span class="short">` 中，评分在 `class="allstar{N}"` 中（N 范围 10-50，除以 10 得 1-5 星）：

```python
comment_pattern = re.compile(r'<span class="short">(.*?)</span>', re.DOTALL)
rating_pattern = re.compile(r'class="allstar(\d+)', re.DOTALL)
```

## 测试结果

测试书名「斗罗大陆」搜索提取 `subject_id=3705820`，成功抓取 17 条短评。

## Session 配置

```python
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Accept": "text/html,application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
})
# 代理自动从 HTTP_PROXY/HTTPS_PROXY 环境变量读取
for proto in ("HTTP", "HTTPS"):
    proxy = os.environ.get(f"{proto}_PROXY")
    if proxy:
        session.proxies[proto.lower()] = proxy
```

## 限制

- 豆瓣可能对高频请求封 IP，建议间隔 1 秒以上
- 网络小说在豆瓣的评论数量和质量参差不齐
- 豆瓣搜索可能返回同名但不同媒介的书籍（如实体书 vs 网络版），需仔细匹配
