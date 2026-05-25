# novel_any — AI 人机协作小说写作系统

> 一个基于 Hermes Agent 的技能包，支持**网络文学**和**传统文学**双线创作。
> 6 个专业 Agent 协作，覆盖大纲构思 → 写作执行 → 精修审查全流程。
> **Python 工具箱做计算，LLM Agent 做判断。**

---

## 快速开始

### 安装

```bash
# 克隆到 Hermes Skills 目录
cd ~/.hermes/skills/
git clone git@github.com:3186218763/novel_any.git
```

### 使用

在 Hermes Agent 中说出以下任一触发词即可启动：

```
写小说  帮我写书  开新书  继续写  审稿  精修
```

首次启动会自动检测：
- 当前目录是否有项目 → 无则进入新建流程
- 写作距今是否超过 7 天 → 提示回顾
- 伏笔是否超期未回收 → 预警提醒

---

## 核心设计理念

### AI 是协作者，不是代笔

三条铁律贯穿所有 Agent：

1. **先表态，再协商** — 遇到决策点时，AI 先给出判断和建议，再请作者回应。不空等。
2. **每次只做一件事** — 完成一步停下让作者确认。不连续执行多步。
3. **大纲是协商基础，不是圣旨** — 写作中发现矛盾主动提出，协商调整。

### Python 计算 + LLM 判断

novel_any 不只是 Markdown 提示词。内置 `novel_tools` Python 工具箱，用代码处理确定性工作，LLM 专注创意判断。

---

## 工作流（三阶段）

```
作者想法
  ↓
Phase 1: 大纲构思     architect + character-designer
  出品：故事大纲、角色卡、章纲、项目模板
  ↓
Phase 2: 写作执行     narrator + consistency-checker + 按需 scene-specialist
  出品：正文章节、伏笔追踪、角色状态、会话日志
  ↓
Phase 3: 精修审查     consistency-checker + polisher
  出品：审查报告、去 AI 味精修、文风统一
```

---

## Agent 阵容（6 个）

| Agent | 角色 | 触发时机 |
|-------|------|---------|
| **architect** | 故事架构师 | 大纲阶段、方向调整 |
| **character-designer** | 角色设计师 | 大纲初稿后、需要新角色 |
| **narrator** | 叙事写手 | 写作阶段每章 |
| **consistency-checker** | 一致性审查员 | 每章后快速检查、每 10 章深度审查、精修阶段 |
| **polisher** | 精修师 | 精修阶段、去 AI 味 |
| **scene-specialist** | 场景专精师 | 按需（打斗/对话/群像/情感高潮/智斗） |

所有 Agent 可以**内联执行**（轻量任务），也可以通过 `delegate_task` **委派独立子会话**（重量任务如全局审查）。

---

## Python 工具箱（novel_tools）

```bash
# 所有命令统一入口
python3 -m novel_tools.cli <模块> <子命令>
```

### 模块速览

| 模块 | 命令 | 功能 |
|------|------|------|
| **stats** | `stats count <file>` | 中文字数、总字符、段落、对话行 |
| | `stats pacing <file>` | 对话/描写/叙述比例、段落密度 |
| | `stats rhythm <file>` | 情绪曲线（40 段归一化） |
| **slop** | `slop scan <file>` | 全维度 AI 检测（TTR、句长变异、结构模式、黑名单密度） |
| | `slop dict --ban` | 查看禁用词（185 个 ban 级） |
| **bible** | `bible char list` | 角色列表 |
| | `bible char add <名> --role <类型>` | 添加角色 |
| | `bible foreshadow plant <描述> --ch <N>` | 埋入伏笔 |
| | `bible foreshadow resolve <id> --ch <N>` | 回收伏笔 |
| | `bible foreshadow warn` | 超期预警 |
| | `bible world add <键> <内容> --hard` | 注册世界观硬规则 |
| **consistency** | `consistency check` | 一键运行所有本地检查 |
| | `consistency names <file>` | 称谓/人名扫描 |
| | `consistency timeline` | 时间线冲突检测 |
| **outline** | `outline parse <file>` | 章纲 → 结构化数据 |
| | `outline diff <正文> <章纲>` | 正文 vs 章纲覆盖差异 |

### 输出格式

所有命令输出 **JSON** 到 stdout，Agent 自动解析后向作者呈现关键信息。不需要手动读 JSON。

### 依赖

- Python ≥ 3.10
- **零外部服务**：SQLite 内置，jieba 分词可选（无 jieba 时以字统计降级）
- 黑名单数据内置（332 条 AI 高频禁用词，7 类 × 3 级）

---

## 两种写作模式

### 网文模式

触发关键词：`起点` `番茄` `晋江` `爽文` `修仙` `玄幻` `都市` `系统` `穿越` `重生` `打脸`

特色：
- 爽点密度控制 + 章末钩子策略
- 读者画像 + 平台适配
- 节奏图谱（每章情绪曲线可视化）
- 升级/打脸/反转节奏规划

### 传统文学模式

触发关键词：`出版` `文学` `严肃` `现实主义` `历史` `纯文学`

特色：
- 人物弧线全景规划
- 主题线索贯穿设计
- 意象连贯性追踪
- 文白程度统一

---

## 项目结构

```
{书名}/
├── context-brief.md          # 入口快照（<3000 字，每次启动加载）
├── 大纲/
│   ├── 故事大纲.md
│   └── 章纲_第N章.md
├── 角色/
│   ├── 角色总览.md
│   └── {角色名}.md
├── 正文/
│   └── 第N章_{章名}.md
├── 追踪/
│   ├── 伏笔账本.md
│   ├── 角色状态.md
│   ├── 时间线.md
│   ├── 章节摘要.md
│   └── 会话日志.md
├── 审查/
│   ├── 全局审查报告.md
│   ├── 一致性检查.md
│   └── 文风检查.md
└── .novel_tools.db          # Bible SQLite 数据库（自动创建）
```

网文项目额外：`读者画像.md` `爽点节奏.md` `世界观/`

传统文学额外：`主题线索.md` `人物弧线全景.md`

---

## [反馈] 自进化机制

在任何阶段说 `[反馈] 具体问题`，系统自动：

1. **定位归属** — 是 Agent 问题？Phase 流程问题？reference 知识不足？
2. **诊断协商** — 展示根因分析，与作者确认
3. **提出修正** — 具体改动方案
4. **执行修正** — 更新 Skills 文件本身
5. **验证** — 告知改动内容和验证方式

```
示例：
  [反馈] 角色对话太生硬，没有辨识度
  [反馈] 大纲太套路化，不够有创意
  [反馈] 写打斗场景总是跳过细节
```

---

## 上下文管理

三层加载，控制 token 消耗：

| 层级 | 内容 | 触发 |
|------|------|------|
| **第 1 层** | context-brief.md + 当前章纲 | 每次必读 |
| **第 2 层** | 出场角色档案 + 相关伏笔 + 前一章正文 | 本章涉及 |
| **第 3 层** | 世界观条目 + 类型 reference | 按需加载 |

---

## 文件结构

```
novel_any/
├── SKILL.md                     # 主入口（路由 + 铁律 + 反馈机制 + 门禁检查）
├── references/
│   ├── agents/                  # 6 个 Agent 提示词
│   │   ├── architect.md         # 故事架构师
│   │   ├── character.md         # 角色设计师
│   │   ├── narrator.md          # 叙事写手
│   │   ├── consistency.md       # 一致性审查员
│   │   ├── polisher.md          # 精修师
│   │   └── scene-specialist.md  # 场景专精师
│   ├── phases/                  # 3 个阶段工作流
│   │   ├── outline.md           # Phase 1 大纲
│   │   ├── writing.md           # Phase 2 写作
│   │   └── polish.md            # Phase 3 精修
│   ├── genre-web.md             # 网文类型参考
│   └── genre-trad.md            # 传统文学类型参考
├── templates/
│   ├── project-web/             # 网文项目模板
│   └── project-trad/            # 传统文学项目模板
├── novel_tools/                 # Python 工具箱
│   ├── cli.py                   # 统一 CLI 入口
│   ├── config.py                # 项目配置加载
│   ├── stats/                   # 文本统计
│   ├── slop/                    # 降 AI 率引擎
│   ├── bible/                   # Story Bible (SQLite)
│   ├── consistency/             # 确定性一致性
│   ├── outline/                 # 大纲管理
│   └── data/                    # 黑名单词库
└── README.md
```

---

## 常见问题

**Q: novel_any 和 NovelForge / novel-writer-master 的区别？**

A: novel_any 是一个 **Hermes Agent Skill**，深度集成在 Hermes 生态中。它不依赖 Streamlit Web UI 或独立 CLI 工具——你直接在终端或 Telegram/Discord 上与 Agent 对话写作。novel_tools 是一个纯计算工具箱，不做界面。

**Q: 可以用现有项目吗？**

A: 可以。将你的小说目录结构对齐 project-web 或 project-trad 模板，创建 `context-brief.md`，novel_any 就会识别并接续你的进度。

**Q: 数据安全吗？**

A: 所有数据存储在本地：`{项目目录}/.novel_tools.db`（SQLite）和 Markdown 文件。不上传任何服务器。LLM 调用走你配置的 Hermes provider。

**Q: 怎么贡献或定制？**

A: Fork 本仓库，修改 `references/` 下的 Agent prompt、添加你自己的 tool 到 `novel_tools/`、或扩展 `templates/`。使用 `[反馈]` 机制可以让 Skills 自我进化。

---

## License

MIT
