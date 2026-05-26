# 豆瓣评论抓取

从豆瓣抓取书籍短评用于 novel_tools 验证。

## 代理要求

国内访问豆瓣需代理。review_scraper 通过 `_get_session()` 自动读取环境变量：

```python
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:10090'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:10090'
```

不设置代理 → SSL EOF 错误。

## 搜索流程

1. 搜索书籍: `https://www.douban.com/search?cat=1001&q={书名}`
2. 提取 subject ID: 豆瓣新搜索结果将链接编码在 `/link2/?url=...` 中
   - 正则: `r'/link2/\?url=.*?subject%2F(\d+)%2F'`
   - 回退(旧版): `r'subject/(\d+)/'`
3. 抓评论: `https://book.douban.com/subject/{id}/comments/`

## 评论提取

```python
comment_pattern = re.compile(r'<span class="short">(.*?)</span>', re.DOTALL)
rating_pattern = re.compile(r'class="allstar(\d+)', re.DOTALL)
# rating = int(rating) // 10 → 0-5 星
```

## 书名清洗

网文标题常有噪音后缀，搜索前需清洗：

```python
def _clean_book_title(title: str) -> str:
    suffixes = ['完结时间', '什么软件能看', '全文免费阅读', '免费阅读',
                '全文阅读', '无弹窗', '笔趣阁', 'txt下载', '精校版']
    for s in suffixes:
        title = title.replace(s, '')
    title = re.sub(r'[（(][^)）]*[)）]', '', title)
    return title.strip()
```

示例:
- `开局签到荒古圣体什么软件能看` → `开局签到荒古圣体`
- `超级上门女婿完结时间` → `超级上门女婿`

## 覆盖率

豆瓣对网文书名匹配率约 38%(5/13 本)。长书名、带符号书名更难匹配。建议补充贴吧抓取（代码已有，默认启用）。
