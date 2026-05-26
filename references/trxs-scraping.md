# trxs.cc Playwright 抓取

trxs.cc（同人小说网）使用 JS 渲染书单和章节，需 playwright headless browser 抓取。

## 为什么用 trxs.cc

- 所有笔趣阁镜像站只返回预览片段（~1000 字）
- trxs.cc 章节完整：2300-4369 中文字符/章（实测）
- 书籍列表 JS 渲染，curl/requests 无法获取

## 先决条件

Playwright + Chromium 已安装。WSL 无 sudo 环境配置见 `references/playwright-wsl-setup.md`。

每次使用前设置：
```bash
export LD_LIBRARY_PATH=~/miniconda3/lib:$LD_LIBRARY_PATH
```

## 书单发现

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page()
    page.goto('https://www.trxs.cc/tongren/', timeout=30000, wait_until='networkidle')
    
    links = page.eval_on_selector_all('a[href]',
        'els => els.map(e => ({h: e.getAttribute("href"), t: e.textContent.trim()}))')
    
    novels = [l for l in links 
              if l['t'] and '/tongren/' in (l['h'] or '')
              and not any(x in l['h'] for x in ['index_','tags-','rating','search'])]
```

## 章节列表

书本页面 URL: `https://www.trxs.cc/tongren/{book_id}/`
章节链接正则: `r'/tongren/\d+/(\d+)\.html'`
URL 中文件名数字即为章节号，需按数字排序。

## 章节内容

```python
page.goto(chapter_url, timeout=30000, wait_until='networkidle')
text = page.eval_on_selector('body', 'el => el.innerText')
text = re.sub(r'document\.write.*|function\s+\w+\([^)]*\).*', '', text)
```

## 性能

| 指标 | 值 |
|------|-----|
| 每章耗时 | ~2 秒 |
| 15 本 x 40 章 | ~20 分钟 |
| 章字数 | 2300-4400 中文字符 |
| 内存占用 | ~500MB (chromium) |

## 书名清洗

trxs.cc 书名含评分/作者/文件大小信息，取第一行并去括号后缀。

## 已知限制

- 首页约 6-8 本独特小说
- 搜索页不返回结构化结果
- 需翻页获取更多（/tongren/index_2.html）
