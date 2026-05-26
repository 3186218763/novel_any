# Pipeline 使用指南

novel_auto_pipeline 的完整使用方法和配置。

## 快速开始

```bash
# 全流程 (抓取 → 分析 → 评论验证 → 审查)
cd /home/miku/.hermes/skills/novel_any
python -m novel_tools.pipeline.pipeline run --limit 5 --max-chapters 10

# 单阶段
python -m novel_tools.pipeline.pipeline fetch --limit 3
python -m novel_tools.pipeline.pipeline analyze --book-id 1
python -m novel_tools.pipeline.pipeline validate --book-id 1
python -m novel_tools.pipeline.pipeline research    # 输出待委派的调研 prompts
python -m novel_tools.pipeline.pipeline review
```

## 发现模式

```python
from novel_tools.pipeline.scraper import discover_and_fetch

# 首页(默认)
discover_and_fetch(limit=5, discovery_mode='homepage')

# 排行榜
discover_and_fetch(limit=5, discovery_mode='ranking')

# 分类页
discover_and_fetch(limit=5, discovery_mode='category:玄幻')
discover_and_fetch(limit=5, discovery_mode='category:xuanhuan')

# 全部方式去重
discover_and_fetch(limit=15, discovery_mode='all')
```

## 评论抓取

```python
from novel_tools.pipeline.review_scraper import scrape_reviews_for_book

# 需要代理
import os
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:10090'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:10090'

stats = scrape_reviews_for_book(book_id, '斗罗大陆', sources=['douban', 'tieba'])
```

## 验证方法论

pipeline 的核心价值不是下载小说，而是通过评论验证工具的准确性：

```
评论说"节奏慢" + 工具 pacing 指标正常 → false_negative (工具漏检)
评论正常 + 工具报异常 → false_positive (工具误报)
两者一致 → matched
```

迭代流程：
1. 跑一轮 pipeline 发现 gaps
2. 分析 gap 根因(指标路径错误？阈值不准？工具缺失功能？)
3. 修工具 → 重跑验证 → 直到 matched 率不再提升

## Cron 定时任务

```bash
# 查看
hermes cron list | grep novel

# 手动触发
hermes cron run <job_id>

# 当前配置: 每周日凌晨 3 点
```

## DB 结构

`pipeline.db` 8 张表:
- `books` / `chapters`: 抓取数据
- `analyses`: 分析结果(每章×每模块)
- `reviews` / `comparisons`: 评论和对比结果
- `gaps` / `research` / `fixes`: 差距追踪和改进记录

## 大规模验证范例

2026-05-26 的 4 轮迭代验证为典型模式：

```python
# 1. 清库重来
from novel_tools.pipeline.db import get_db
db = get_db()
for t in ['comparisons','gaps','reviews','analyses','chapters','books']:
    db.execute(f'DELETE FROM {t}')
db.commit()

# 2. 多类型抓取 (13 本 × 40 章 = 512 章)
for cat in ['玄幻','武侠','都市','历史','网游','科幻','女生']:
    discover_and_fetch(limit=2, max_chapters=40, discovery_mode=f'category:{cat}')
discover_and_fetch(limit=1, discovery_mode='homepage')

# 3. 全量分析 + 评论 + 验证
for book in list_active_books():
    analyze_book(book['id'])
    scrape_reviews_for_book(book['id'], clean_title, sources=['douban'])
    validate_book(book['id'], run_id)

# 4. 分析 gap → 修工具 → 清 comparison/gap → 重跑 validate(无需重分析)
#    迭代 4 轮: 3.8% → 30.2% → 49.7% → 61.6%
```

**关键教训**：
- 排行榜 (`/top/`) 前几页多为成人向内容，优先用分类页
- 书名需先清洗噪音后缀（"完结时间"\"什么软件能看"等）再搜豆瓣
- 仅 2-3 本书能匹配到豆瓣评论，其他需贴吧补充或手动导入
