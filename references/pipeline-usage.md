# Pipeline Usage

novel_auto_pipeline 是一个 6 阶段自动化闭环：抓取 → 分析 → 评论抓取 → 验证 → 调研 → 改进。

## CLI

```bash
# 全流程
python -m novel_tools.pipeline.pipeline run --limit 5 --max-chapters 40

# 单阶段
python -m novel_tools.pipeline.pipeline fetch --limit 5
python -m novel_tools.pipeline.pipeline analyze --book-id 1
python -m novel_tools.pipeline.pipeline validate --book-id 1
python -m novel_tools.pipeline.pipeline research
python -m novel_tools.pipeline.pipeline review

# 发现模式
python -m novel_tools.pipeline.pipeline run --limit 5 --max-chapters 40  # 默认 homepage
python -c "from novel_tools.pipeline.scraper import discover_and_fetch; discover_and_fetch(limit=3, max_chapters=40, discovery_mode='ranking')"
python -c "from novel_tools.pipeline.scraper import discover_and_fetch; discover_and_fetch(limit=3, max_chapters=40, discovery_mode='category:玄幻')"
python -c "from novel_tools.pipeline.scraper import discover_and_fetch; discover_and_fetch(limit=10, max_chapters=40, discovery_mode='all')"
```

## Cron

```bash
hermes cron list | grep novel    # 查看任务
hermes cron run <job_id>          # 手动触发
hermes cron pause <job_id>        # 暂停
```

## 数据库

`pipeline.db` 位于 `data/pipeline/pipeline.db`，8 张表：

| 表 | 说明 |
|----|------|
| books | 小说元信息 |
| chapters | 已抓取章节 |
| analyses | 分析记录（每章×每模块） |
| reviews | 读者评论 |
| comparisons | 评论 vs 分析对比 |
| gaps | 发现的差距（去重） |
| research | 调研记录 |
| fixes | 改进记录 |

## 代理

评论抓取（豆瓣）需要代理。设置环境变量：

```bash
export HTTP_PROXY=http://127.0.0.1:10090
export HTTPS_PROXY=http://127.0.0.1:10090
```

## 已知局限

- bqglll.cc `?get=content` 返回 1079 字预览片段，非完整章节
- 豆瓣对网文书名匹配率有限（长书名/带符号的匹配不上）
- 评论→维度映射依赖关键词，语义层面的抱怨难以捕获
