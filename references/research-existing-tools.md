# 业界小说写作工具调研

> 调研日期: 2026-05-25
> 目的: 为 novel_any Python 工具箱设计提供参考

## 调研项目总览

| 项目 | Stars | 语言 | 形态 | 核心价值 |
|------|-------|------|------|---------|
| RhythmicWave/NovelForge | 867 | Python | Web (FastAPI) | 卡片创作、JSON Schema 结构化生成、伏笔追踪 API、一致性校验、关系图谱 |
| Tomsawyerhu/Chinese-WebNovel-Skill | 273 | Python | Skill (Codex) | 74+ 网文摘录语料库、模仿索引、质量检查清单 |
| raestrada/storycraftr | 139 | Python | CLI | 世界观构建、大纲生成、章节写作 |
| BiranSama/ReNovel-AI | 126 | Python | Web (NiceGUI) | RAG 长时记忆、三模态协作(作家/主编/助手)、卡片流式编辑器 |
| qiuxinyuan321/novel-writer-master | 1 | Python | Web (Streamlit) | 降 AI 率引擎、Story Bible、一致性检查、分层大纲、仪表盘 |

## novel-writer-master 详细分析（已克隆到 /tmp/）

### 模块架构

```
src/novel_writer/
├── core/           # 核心框架（模块注册、事件系统）
├── llm/            # LLM 路由 + prompt 模板
├── models/         # SQLAlchemy 数据模型
├── modules/
│   ├── anti_slop/  # ★ 降 AI 率引擎
│   ├── bible/      # Story Bible (角色/世界观/伏笔 CRUD)
│   ├── consistency/# 一致性检查
│   ├── dashboard/  # 进度统计 + 情绪节奏图
│   ├── outline/    # 分层大纲管理
│   ├── export/     # 导出
│   ├── generation/ # 文本生成
│   ├── project/    # 项目管理
│   └── settings/   # 配置
├── ui/             # Streamlit 页面
├── config.py
└── db.py
```

### 降 AI 率引擎 (anti_slop/) — ★ 核心参考

**分析器 (analyzer.py):**

- **TTR (Type-Token Ratio)**: unique_words / total_words，AI 文本通常 TTR 偏低
- **Hapax Ratio**: 只出现一次的词占比，高 = 更"人类"
- **句长变异系数**: std(sentence_lengths) / mean，低变异 = AI 特征
- **结构模式检测**: 7 种 AI 典型句式（三段并列、总分总、不仅…而且、不是…而是、一方面…另一方面、虽然…但是、因为…所以）
- **句式重复度**: 相邻句子长度比 + 词汇重叠度

**黑名单词库 (dictionary.py):**

- 332 个词条，JSON 格式
- 7 个分类: connector(27), filler(14), action(67), emotion(63), dialogue(41), cliche(64), narration(56)
- 3 个严重级别: ban(185), warn(116), limit(31)
- 示例: 然而[connector/ban], 不禁[filler/ban], 显然[filler/ban], 不由得[filler/ban]
- 支持按分类/级别过滤、随机抽样注入 prompt

**评分器 (scorer.py):** 综合 TTR + 句长变异 + 黑名单密度 + 结构模式 → 综合 AI 风险评分

### Story Bible (bible/)

- 角色 CRUD: name/role/profile/speech_style (patterns/vocab_level/dialect/catchphrases/forbidden_words/tone)
- 世界观 CRUD: category/key/content/is_hard_rule
- 伏笔 CRUD: name/description/status/plant_chapter/resolve_chapter

### 一致性检查 (consistency/)

- LLM 驱动，Jinja2 prompt 模板
- 分 5 维度: 角色/世界观/时间/称谓/伏笔
- 输入: 本章内容 + 角色列表 + 世界观规则 + 前 3 章摘要
- 输出: 结构化 Issue 列表(category/description/quote/suggestion)

### 大纲管理 (outline/)

- 分层树形结构: volume → chapter → scene
- 每节点含: narrative_goal, emotion_target, checkpoints
- 创建章级大纲时自动创建对应 Chapter 记录

### 依赖项

```toml
dependencies = [
    "fastapi", "uvicorn", "sqlalchemy", "streamlit",
    "openai", "jieba", "jinja2", "pyyaml", "pydantic",
    "pydantic-settings", "httpx"
]
```

## NovelForge 关键参考点

- **伏笔追踪**: suggest/list/register/resolve 完整 API
- **一致性校验**: CheckRequest(text + facts_structured) → CheckResponse(issues + suggested_fixes)
- **关系图谱**: 角色/地点/事件之间的结构化关系
- **上下文管理**: context endpoint 聚合项目上下文

## Chinese-WebNovel-Skill 关键参考点

- **模仿索引**: 74+ 篇小说摘录，按标签分类（系统/攻略、弹幕/评论、真假千金、古言/宫廷等）
- **语料库构建脚本**: build_webnovel_corpus_assets.py, scrape_yanxuan_recent_posts.py
- **质量检查清单**: webnovel_quality_checklist.md

## 对 novel_any 的启示

1. **anti_slop 可直接借鉴**: 分词用 jieba，指标计算纯本地，毫秒级
2. **bible 的数据模型值得参考**: speech_style 的设计对角色一致性很有用
3. **consistency 的 LLM 驱动方式与我们的 Agent 模式天然契合**
4. **outline 的分层结构 + checkpoint 机制比我们当前的章纲模板更结构化**
5. **332 条黑名单可以直接复用**（MIT 协议）
