# novel_auto_pipeline — 自动化持续改进流水线

> 完整设计文档: `docs/superpowers/specs/2026-05-26-novel-auto-pipeline-design.md`

## 6 阶段流水线

1. **抓取** — 从 bqglll.cc 下载免费章节 → `.md` 文件
2. **分析** — 运行 stats/slop/consistency/style_lint 全部模块
3. **验证** — 抓取评论（起点本章说/豆瓣/贴吧），LLM 提取维度标签，与工具输出对比
4. **调研** — `delegate_task` 委派 subagent，搜索 GitHub/arXiv/博客解决方案
5. **改进** — `delegate_task` 委派 subagent，独立分支实现，运行回归测试
6. **审查** — 导入检查 + 功能回归 + 效果验证，通过则合并

## 触发方式

- 定时: `hermes cron` 每周日凌晨 3 点
- 手动: `python -m novel_tools.pipeline run`
- 部分运行: `--phase fetch|analyze|validate|research|improve|review`

## 状态数据库

`pipeline.db` SQLite: books → chapters → analyses → reviews → comparisons → gaps → research → fixes

## 维度映射表

| 评论高频词 | 维度 | 对应模块 |
|-----------|------|---------|
| 节奏慢/拖/水文 | pacing | pacing.py |
| 角色崩/人设不对 | character_consistency | names.py, character.py |
| AI/套路/模板 | ai_score | analyzer.py, scanner.py |
| 读不下去/太绕 | readability | wordcount.py |
| 情绪平/没起伏 | emotion_arc | emotion.py |
| 啰嗦/废话多 | redundancy | style_lint/rules.py |
| 时间混乱/bug | timeline | timeline.py |
| 跑题 | outline_deviation | diff.py |

## 关键设计决策

- 方案 B (单体 Pipeline + SQLite) 而非过度工程化的事件驱动架构
- 改进环节委托 subagent 而非内联（上下文隔离）
- LLM 做评论维度提取（口语化不适合纯规则）
- bqglll.cc 为主要抓取源

## Scraper 技术细节

- bqglll.cc 移动端 (`m`) 章节页被 Cloudflare JS Challenge 完全拦截，cloudscraper/curl_cffi 均无法绕过
- **解决方案**: 桌面版 (`www.bqglll.cc`) + URL 追加 `?get=content` 触发服务端渲染
  - 书籍信息页/章节列表在 `<dd>` 标签中，`href` 后可能有空格
  - cloudscraper 配置: `browser={'browser':'chrome','platform':'windows','mobile':False}`
- 章节列表提取: `<dd><a href ="/look/{id}/{ch}.html">标题</a></dd>`
- 正文容器 ID 优先级: `chaptercontent` > `content` > `txt` > `article` > `nr1`

## Validator 指标提取（已修复）

各模块输出的 metrics 结构不同，validator 使用 dotted-path 解析：

| 维度 | metric_path | 来源模块 | 实际 key |
|------|------------|---------|----------|
| pacing | `action_density` | pacing.py (直接 key) | 非 `density` — 注意命名差异 |
| readability | `readability.flesch_zh` | stats/wordcount.py (嵌套) | 注意 `readability.flesch_zh` 而非直接 `flesch_zh` |
| ai_score | `risk.score` | slop/analyzer.py (嵌套) | 注意 `risk.score` 而非 `ai_score` |
| redundancy | `total_issues` | style_lint/rules.py (直接 key) | 注意 `total_issues` 而非 `redundancy_count` |
| emotion_arc | `variance` | consistency/emotion.py (直接 key) | 嵌套在 curve 数组内 |

## 实现教训

- **指标路径对齐是关键坑**: `analyzer.py` 统一调用各模块，但各模块输出结构不统一（有些扁平、有些嵌套），validator 的 `_tool_normal_metrics_for_dimension` 必须用 dotted-path 解析 `readability.flesch_zh` 这类嵌套路径
- **add_manual_reviews 接受多行字符串**（每行一条评论），不接受 list — 避免 DB 主键冲突
- **pacing 的输出 key 是 `action_density`** 而非 `density` — 设计文档中的阈值定义需要与实际输出对齐
- **阈值量纲要匹配**: `action_density` 是「每 1000 字符中的动作元素数量」(范围 ~10-50)，不是 0-1 的比例。正确的阈值是 **15**（<15 = 节奏慢），而非最初错误设置的 **0.4**。此 bug 导致 validator 将 pacing 正常的章节误判为 false_negative。
