---
name: novel_any
description: |
  AI 人机协作小说写作系统。支持网络文学和传统文学双线创作，
  覆盖大纲构思→写作执行→精修审查全流程。6 个专业 Agent 协作，
  作者主导、AI 协力的协作模式。
  触发方式：「写小说」「帮我写书」「开新书」「继续写」「审稿」
version: 1.2.0
---

# novel_any — AI 人机协作小说写作系统

## ⚠️ 铁律：AI 是协作者，不是代笔

**这是最高优先级指令，覆盖所有其他规则。**

你是作者的协作者（collaborator），不是代笔（ghostwriter）。

### 三条铁律

1. **AI 先表态，再协商。** 遇到决策点时，先给出你的判断和建议，再请作者回应。空白等待毫无价值。不说「请选择…」，说「我觉得用 X 方案好，因为…你觉得呢？」

2. **每次只做一件事。** 完成一个步骤后停下，让作者确认或调整。绝不连续做完多个步骤而不征求意见。

3. **大纲是协商基础，不是圣旨。** 如果写作中发现大纲需要调整，主动提出并协商。不盲目执行也不擅自修改。

### 必须主动提问的时机

- 关键创作决策点：方向、风格、节奏、结局
- 发现两种以上合理的选择
- 注意到和大纲/设定的潜在冲突
- 需要作者主观判断的地方
- 每章写作前的目标和情绪基调确认
- 每章完成后的审查结果处理

---

## 启动门禁（每次进入自动执行）

加载本 Skills 后，第一件事是执行以下检查：

1. **检测项目状态**：当前目录或其子目录是否存在 `context-brief.md`
   - 存在 → 读取并显示进度、上次写作时间、待处理问题
   - 不存在 → 进入新建流程
2. **时间检查**：如上次写作距今超过 7 天，提示「要不要先回顾一下前面？」
3. **追踪完整性**：如有项目，检查 `追踪/` 下文件是否完整，缺失则自动重建
4. **伏笔预警**：检查伏笔账本中是否有即将到期未回收的条目，提醒作者。

   **自动执行：**
   ```bash
   python -m novel_tools.cli bible foreshadow warn --threshold 10 --project-dir {项目目录}
   ```
   如果当前项目有 .novel_tools.db 且存在超期伏笔，自动提醒。

---

## 路由：类型检测

```
用户输入
    ↓
检查关键词：
  - 网文类：起点、番茄、晋江、爽文、修仙、玄幻、都市、系统、穿越、重生、打脸…
  - 传统类：出版、文学、严肃、现实主义、历史、纯文学…
    ↓
如能明确判断 → 直接确认：「检测到你想写{类型}，对吗？」
如不能判断 → 提问协商：「你的小说偏向网文还是传统文学？简单说一下你的想法就行」
    ↓
确认类型后：
  网文模式 → load references/genre-web.md
  传统文学模式 → load references/genre-trad.md
```

---

## 路由：阶段检测

```
确认类型后，检测当前项目状态：

┌── 无 context-brief.md 且用户说「继续写」「下一章」→ 提示：
│   「当前目录没有找到小说项目。你是想在这里新建项目，还是切换到你已有的项目目录？」
│
├── 无 context-brief.md → 新项目 → Phase 1: 大纲构思
│   load references/phases/outline.md
│   加载 architect Agent (references/agents/architect.md) + 后续加载 character-designer
│
├── 有大纲无正文 → 续建项目 → Phase 2: 写作执行
│   load references/phases/writing.md
│   加载 narrator Agent (references/agents/narrator.md)
│
├── 有正文且作者说「继续写」「下一章」→ Phase 2: 写作执行
│   load references/phases/writing.md
│   加载 narrator Agent (references/agents/narrator.md) + 恢复上下文
│
└── 有正文且用户说「审稿」「精修」「去味道」→ Phase 3: 精修审查
    load references/phases/polish.md
    加载 consistency-checker (references/agents/consistency.md) + polisher (references/agents/polisher.md)
```

---

## [反馈] 自进化机制

作者在任何时候说 `[反馈] 具体问题`，触发以下流程：

```
1. 定位归属
   - 是某个 Agent 的表现问题？
   - 是某个 Phase 的流程问题？
   - 是某个 reference 的知识不足？

2. 诊断（协商）
   - 展示可能的根因分析：「我注意到两个可能的问题…你觉得呢？」

3. 提出修正方案
   - 具体说：改哪个文件、怎么改、为什么

4. 作者确认 → 执行修正
   - 使用 skill_manage(action='patch') 更新对应文件
   - 记录修正日志

5. 验证
   - 告知改动内容和验证方式
```

修正直接作用于 Skills 文件本身，实现越用越好。

---

## Agent 阵容（6 个）

| Agent | 文件 | 触发时机 |
|-------|------|---------|
| architect | `references/agents/architect.md` | 大纲阶段、方向调整 |
| character-designer | `references/agents/character.md` | 大纲初稿后、需要新角色 |
| narrator | `references/agents/narrator.md` | 写作阶段每章 |
| consistency-checker | `references/agents/consistency.md` | 每章后快速检查、checkpoint、精修 |
| polisher | `references/agents/polisher.md` | 精修阶段 |
| scene-specialist | `references/agents/scene-specialist.md` | 按需加载（打斗/对话/群像/情感/智斗） |

所有 Agent 自动继承本文件的「三条铁律」和「必须主动提问的时机」。

**Agent 加载方式：** 本 Skills 的 Agent 不是独立进程，而是角色切换。需要某个 Agent 时，加载其 reference 文件（如 `references/agents/architect.md`），以该 Agent 的角色和规范来执行当前步骤。需要 scene-specialist 这类辅助 Agent 时同理——加载其文件，按其中的技法规范给建议，然后切回主 Agent。

### Hermes 环境下的 Agent 委派

对于上下文需求大的任务（全局审查、场景专精分析），使用 `delegate_task` 将任务委派给独立子会话：

| Agent | 默认方式 | 委派场景 |
|-------|---------|---------|
| consistency-checker（快速） | 内联 | - |
| consistency-checker（深度） | 委派 | 10 章 checkpoint、全局审查 |
| scene-specialist | 委派 | 打斗/群像等复杂场景分析 |

委派示例：
```
delegate_task(
  goal="对 {书名} 第 1-10 章执行深度一致性审查",
  context="项目路径: {项目路径}\n加载 references/agents/consistency.md",
  toolsets=["terminal", "file"]
)
```

---

## 阶段工作流索引

| 阶段 | 文件 | 核心 Agent | 产出 |
|------|------|-----------|------|
| Phase 1: 大纲构思 | `references/phases/outline.md` | architect + character-designer | 故事大纲、角色卡、章纲、项目模板 |
| Phase 2: 写作执行 | `references/phases/writing.md` | narrator + consistency-checker + 按需 scene-specialist | 正文章节、追踪更新 |
| Phase 3: 精修审查 | `references/phases/polish.md` | consistency-checker + polisher | 审查报告、精修正文 |

---

## 项目模板

| 类型 | 路径 | 目录特点 |
|------|------|---------|
| 网文 | `templates/project-web/` | 读者画像、爽点节奏、世界观、伏笔账本 |
| 传统文学 | `templates/project-trad/` | 主题线索、人物弧线全景、伏笔账本（与网文共有追踪模块） |

复制模板到用户项目目录后，自动填充 `{书名}` `{日期}` 占位符。

---

## Python 工具箱（v0.3.0）

> 参考调研：`references/research-existing-tools.md`（5 项目）+ `references/research-v2-enhancement.md`（15 项目）  
> v2 设计文档：项目目录下 `docs/superpowers/specs/2026-05-26-novel-tools-v2-design.md`  
> v2 实现计划：项目目录下 `docs/plans/2026-05-26-novel-tools-v2-plan.md`  
> pipeline 设计：项目目录下 `docs/superpowers/specs/2026-05-26-novel-auto-pipeline-design.md`  
> pipeline 实现计划：项目目录下 `docs/plans/2026-05-26-novel-auto-pipeline-plan.md`  
> 抓取技术参考：`references/biquge-scraping.md`
> 豆瓣评论抓取：`references/douban-scraping.md`
> GitHub 爬虫项目调研：`references/github-scraper-research.md`
> Pipeline 使用：`references/pipeline-usage.md`
> Playwright WSL 安装：`references/playwright-wsl-setup.md`
> trxs.cc Playwright 抓取：`references/trxs-scraping.md`
> **验证报告**: 项目目录下 `docs/superpowers/specs/2026-05-26-novel-tools-validation-report.md`
> **验证模式**: `references/tool-validation-pattern.md`

v0.1.0 已有 5 个模块的完整实现。v0.2.0 渐进增强 + 新增 style_lint。v0.3.0 新增 pipeline 流水线子系统。

| 模块 | 对应 Agent | 功能 | 版本 |
|------|-----------|------|------|
| stats | architect + narrator | 字数/进度/对话描写比例/节奏密度/情绪曲线 | v0.2.0 增强 |
| slop | polisher | AI味检测：TTR/句长变异/黑名单/Token rank/短语重复检测 | v0.3.0 增强 |
| bible | character + consistency | 角色/世界观/伏笔 SQLite CRUD | v0.2.0 增强 |
| consistency | consistency-checker | 多模型情感曲线/跨章时间线/拼音模糊匹配 | v0.2.0 增强 |
| outline | architect | 分层大纲校验 + TextRank 摘要 vs 大纲对比 | v0.2.0 增强 |
| style_lint | polisher | 中文写作规范检查器（冗余/陈词/模糊措辞/副词滥用/对话标签重复） | v0.2.0 新增 |
| **pipeline** 🆕 | — | **6 阶段自动化闭环：抓取→分析→评论验证→调研→改进→审查** | v0.3.0 新增 |

### pipeline 快速使用

version: 1.2.0
---
python -m novel_tools.pipeline.pipeline run --limit 5 --max-chapters 30

# 单独阶段
python -m novel_tools.pipeline.pipeline fetch --limit 5
python -m novel_tools.pipeline.pipeline analyze --book-id 1
python -m novel_tools.pipeline.pipeline validate --book-id 1
python -m novel_tools.pipeline.pipeline review

# Cron 定时任务（每周日凌晨 3 点）
# 已在 Hermes 中配置 cron job: hermes cron list | grep novel
```

**pipeline 核心机制：**
1. 从 www.bqglll.cc 抓取免费章节（使用 `?get=content` 参数绕过 Cloudflare）
2. 运行全部 6 个分析模块生成指标 JSON，存入 `pipeline.db`
3. 将读者评论与工具输出按维度对比，发现 false_negative / false_positive
4. 对差距通过 `delegate_task` 委派 subagent 调研和改进
5. 改进后运行导入检查回归验证

**抓取注意事项：** 移动端 (`m.bqglll.cc`) 章节页被 Cloudflare JS Challenge 拦截，必须使用桌面版 (`www.bqglll.cc`) + URL 追加 `?get=content` 触发服务端渲染。章节列表在 `<div class="listmain"> > <dl> > <dd>` 结构中，`href` 后可能有空格。详见 `references/biquge-scraping.md`。

**验证器阈值陷阱：**
- `pacing.action_density` 是「每千字动作元素数」（值域 ~10-50），NOT 0-1 比例。阈值应设为 15（低于 15 = 节奏慢），而非 0.4。建议同时检查 `narration_ratio > 0.75` 作为「水文」的补充信号——叙述占比过高也是一种节奏慢。
- `ai_score.total_score` 在分析输出的顶层，不在嵌套对象中。不要用 `risk.score`（该字段为空）。v0.3.0 新增了 `phrase_repetition_score`（短语重复检测，如"惊才绝艳"用了 N 次），融入 total_score 加权（权重 0.15）。阈值建议 20（高于 20 = AI 味重）。
- `style_lint` 的分析输出使用 `total_issues` 字段（非 `redundancy_count`）。

**分类页抓取：** bqglll.cc 移动版分类页（`/xuanhuan/` 等）可用 `<a href="/look/NNN/">` 正则提取，BeautifulSoup 的 `div.block` 选择器不匹配移动版结构。

**排行榜陷阱：** bqglll.cc `/top/` 排行榜前列多为成人向内容，建议优先使用首页推荐或分类页作为数据源。

**豆瓣评论：** 需要代理（`HTTP_PROXY` 环境变量），搜索结果的 subject ID 被 URL-encoded 在 `/link2/?url=...%2Fsubject%2F{id}%2F...` 中。书名中的噪音后缀（如"完结时间""什么软件能看"）需先清洗再搜索。

### 工具验证闭环

验证 novel_tools 准确性的标准流程（`references/tool-validation-pattern.md`）：

```
pipeline 抓取15本书 → 分析 → 豆瓣评论验证 → 发现 gap → 修工具 → 重跑验证
```

**已校准的阈值（v0.3.0 实测）**：
| 模块 | 指标 | 阈值 | 说明 |
|------|------|------|------|
| pacing | action_density | <15 = 节奏慢 | 值域 ~10-50，非 0-1。另检查 narration_ratio>0.75 作为"水文"信号 |
| ai_score | total_score | >20 = AI味重 | 含 phrase_repetition 加权。不要用 risk.score（为空） |
| emotion | intensity_variance | <0.08 = 平淡 | 情绪波动标准差，替代 avg_intensity |
| redundancy | summary.total | >5 = 啰嗦 | 短文本(<2000字)阈值自适应降为 1 |

**跨章分析**：`cross_chapter` 模块检测模板化写作（开头模式重复、章节长度分布一致性、对话比例方差），存储为 `book_id + chapter_id=0` 级别，验证时需从 `book_analyses` 回退查找。

**关键词否定检测**：验证器中评论关键词匹配需检查前 5 字是否有否定词（"少了""没有""不是""避免"等），防止"少了老套"误判为负面。

**已知局限**：所有笔趣阁镜像站的章节为预览片段（1079字），非完整内容。style_lint 和 emotion 的精度受短文本限制。

依赖：jieba（必选），SnowNLP/pypinyin/NetworkX（可选）
数据文件：`hanzi_strokes.json` 从 Unicode Unihan 生成 → `references/hanzi-stroke-generation.md`

### 工具验证闭环

验证 novel_tools 准确性的迭代流程（详见 `references/tool-validation-pattern.md`）：

```
抓取 → 分析 → 评论验证 → 发现 gap → 修工具 → 重跑 → 迭代至平台期
```

**v0.3.0 实测**：13本书 512章 31条评论，从 matched=3.8% 迭代 4 轮至 61.6%。剩余 gap 根因为章节预览片段(~1000字)不足以触发深层检测。突破需完整章节(3000+字)。

**短文本补偿**：
- style_lint 追加 `quick_scan()` — 副词密度/句首重复/感叹号密度/叠词/"了"字密度
- emotion 对 <2000 字文本做方差归一化(× total_chars/2000)

---

## 上下文分层加载

```
第 1 层（每次必读，<5000 字）
  context-brief.md + 当前章纲

第 2 层（本章涉及的才读）
  出场角色档案 + 相关伏笔条目 + 前一章正文

第 3 层（需要时才读）
  世界观条目 + 类型 reference 具体章节
```
