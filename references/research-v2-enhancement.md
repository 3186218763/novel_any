# novel_tools v2 增强调研 — 15 个开源项目

> 调研日期: 2026-05-26
> 目的: 为 novel_any 工具箱 v0.2.0 增强提供思路

## 一、风格检查与写作规范

### proselint (4.3k ⭐, Python)
"A linter for prose" — 25+ 模块化散文检查：冗余/模糊措辞/陈词/古语/混合隐喻。
对 novel_any 启发：模块化检查架构直接借鉴为 style_lint。

### write-good (4.9k ⭐, JS)
英文被动语态/cliche/弱化词/赘余检测，编辑器插件。
启发：纯正则规则引擎 + "建议而非强制"哲学。

### textstat (Python)
15 种可读性公式：Flesch/SMOG/ARI/Dale-Chall。含多语言适配版。

## 二、AI 生成文本检测

### GLTR (IBM-MIT, Python+JS)
逐 token 概率排名着色分析。核心洞察：机器选高概率 token，人类包含更多"意外"选择。
对 slop 启发：token rank 分布分析，无需训练专用二分类器。

### HC3
中英双语 AI 检测。语言学特征版无需 GPU — 句长分布/词汇多样性/情感倾向/标点密度。
对 slop 启发：作为 token rank 的降级路径。

## 三、书籍级 NLP 分析

### BookNLP (UCB, Python+BERT)
人物名聚类(F1 76%)、说话人识别(F1 86%)、事件标注(F1 70%)、超语义标注。
对 bible 启发：实体链接、说话人归属、POV 追踪。

### book_glancer (Python+Streamlit)
NER 角色提取 + 本地 LLM 角色人格推断 + 词云。

## 四、情感与叙事弧线

### SentimentArcs (Python)
数十种情感模型集成 + 滑动窗口平滑 + Kurt Vonnegut 六弧线分类。
对 consistency/emotion 启发：多模型集成 + 弧线分类。

### LLM-TV-Series-Analysis (Python+NetworkX)
角色关系网络图 + 零样本主题分类(BART-MNLI) + 图论叙事分析。
对 bible 启发：共现分析 → 关系图。

## 五、词汇与语言复杂度

### lexical_diversity (Python)
MTLD/HD-D/MATTR — 不受文本长度影响的词汇多样性指标。
关键洞察：简单 TTR 随文本增长系统性下降，MTLD 和 HD-D 消除了此偏差。

## 六、中文 NLP 工具

### SnowNLP (Python)
零依赖中文 NLP：分词/词性/情感分析/TextRank 摘要/相似度(BM25)/繁简转换。

### HarvestText (Python)
实体链接("关云长"→"关羽") + 新词发现 + TextTiling 自动分段 + 依存句法。

### pycorrector (Python)
多模型中英文纠错：Kenlm/T5/MacBERT/Qwen2.5。

## 七、写作工具

### novelWriter (2.4k ⭐, Python)
纯文本存储+树形项目结构+角色地点管理+写作进度追踪。

## 汇总：对 novel_tools 各模块的借鉴

| novel_tools 模块 | 主要借鉴 |
|-----------------|---------|
| **stats** | lexical_diversity(MTLD/HD-D), textstat(可读性), SnowNLP(中文分词) |
| **slop** | GLTR(token rank), HC3(语言学特征), proselint(weasel规则) |
| **bible** | BookNLP(实体链接), HarvestText(别名归一化), LLM-TV-Series(关系图) |
| **consistency** | SentimentArcs(情感弧线), BookNLP(事件标注), pycorrector(纠错) |
| **outline** | SnowNLP(TextRank), HarvestText(TextTiling) |
| **style_lint** 🆕 | proselint(架构), write-good(规则设计), cheatsheet_zh(自定义词典) |
