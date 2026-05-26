# novel_any 工具箱增强调研 — 15 个开源项目

> 调研日期: 2026-05-26
> 目的: 为 novel_tools v0.1.0 → v0.2.0 优化提供借鉴

---

## 风格检查与写作规范

### 1. proselint
- **GitHub**: https://github.com/amperser/proselint
- **Stars**: 4.3k | **语言**: Python
- **核心**: 散文 Linter，25+ 模块化检查（冗余/模糊措辞/陈词/古语/混合隐喻）
- **借鉴**: 插件化检查架构，每个检查独立模块，返回 error/warning/suggestion 三级

### 2. write-good
- **GitHub**: https://github.com/btford/write-good
- **Stars**: 4.9k | **语言**: JavaScript
- **核心**: 英文被动语态/cliche/弱化词/赘余检测，编辑器插件
- **借鉴**: AST 级文本分析，可自定义词典，"建议而非强制"的设计哲学

### 3. textstat
- **GitHub**: https://github.com/textstat/textstat
- **Stars**: — | **语言**: Python
- **核心**: 15 种可读性公式（Flesch/SMOG/ARI/Dale-Chall 等）
- **借鉴**: 章节级可读性曲线辅助分析叙事节奏变化

---

## AI 生成文本检测

### 4. GLTR
- **GitHub**: https://github.com/HendrikStrobelt/detecting-fake-text
- **论文**: arxiv.org/abs/1906.04043
- **Stars**: — | **语言**: Python + JS
- **核心**: IBM-MIT 出品，逐 token 概率排名着色分析，利用 LM 自身的采样偏差反向检测
- **借鉴**: Token rank 分布分析 → 无需训练二分类器，直接用 LM 推理即可。可视化着色标记"AI 感强"的段落

### 5. HC3 (chatgpt-comparison-detection)
- **GitHub**: https://github.com/Hello-SimpleAI/chatgpt-comparison-detection
- **Stars**: — | **语言**: Python
- **核心**: 中英双语 AI 检测，语言学特征版无需 GPU
- **借鉴**: 特征工程方法：句长分布、词汇多样性、情感倾向、标点模式

---

## 书籍级 NLP 分析

### 6. BookNLP
- **GitHub**: https://github.com/booknlp/booknlp
- **Stars**: — | **语言**: Python (spaCy + BERT)
- **核心**: UCB 出品，专为长篇文学设计。人物名聚类(76% F1)、说话人识别(86% F1)、事件标注(70% F1)、超语义标注
- **借鉴**: 人物名聚类远强于字符串匹配；说话人归属→"展示 vs 讲述"比率；POV 追踪→视角切换频率

### 7. book_glancer
- **GitHub**: https://github.com/treefungus/book_glancer
- **Stars**: 1+ | **语言**: Python (Streamlit)
- **核心**: NER 角色提取 + 本地 LLM 角色人格推断 + 词云
- **借鉴**: 用 LLM 聚合角色对话→推断性格特征→"角色圣经"自动化

---

## 情感与叙事弧线

### 8. SentimentArcs
- **GitHub**: https://github.com/jon-chun/sentimentarcs_notebooks
- **Stars**: 43+ | **语言**: Python (Jupyter)
- **核心**: 数十种情感模型集成 + 滑动窗口平滑 + Kurt Vonnegut 六弧线分类
- **借鉴**: 多模型投票/取平均，模型分歧=文学张力标记。滑动窗口（每500词，重叠250词）→ 比简单分句更流畅

### 9. LLM-TV-Series-Analysis
- **GitHub**: https://github.com/pointer2Alvee/llm-tv-series-analysis
- **Stars**: 1+ | **语言**: Python (PyTorch/spaCy/NetworkX)
- **核心**: 角色关系网络(NetworkX) + 零样本主题分类(BART-MNLI) + 图论叙事分析
- **借鉴**: 共现分析→关系图；零样本分类→无标注即可分主题；图密度→叙事复杂度

---

## 词汇与语言复杂度

### 10. lexical_diversity
- **GitHub**: https://github.com/kristopherkyle/lexical_diversity
- **Stars**: — | **语言**: Python
- **核心**: MTLD/HD-D/MATTR — 不受文本长度影响的词汇多样性指标
- **借鉴**: 替代简单 TTR（TTR 随文本增长系统性下降）；过滤虚词后算实词多样性更有意义

---

## 中文 NLP 工具

### 11. SnowNLP
- **GitHub**: https://github.com/isnowfy/snownlp
- **Stars**: — | **语言**: Python
- **核心**: 零依赖中文 NLP：分词/词性/情感/TextRank 摘要/繁简转换/BM25 相似度
- **借鉴**: TextRank 摘要 vs 大纲 diff；BM25 检测章节雷同

### 12. HarvestText
- **GitHub**: https://github.com/blmoistawinde/HarvestText
- **Stars**: — | **语言**: Python
- **核心**: 实体链接("关云长"→"关羽") + 新词发现 + TextTiling 自动分段 + 依存句法
- **借鉴**: 实体链接对 bible 人物管理极有价值；新词发现→奇幻/武侠专有名词自动识别

### 13. pycorrector
- **GitHub**: https://github.com/shibing624/pycorrector
- **Stars**: — | **语言**: Python
- **核心**: 多模型中文纠错: Kenlm/T5/MacBERT/Qwen2.5
- **借鉴**: consistency 模块的结果可接入纠错增强

---

## 写作工具

### 14. novelWriter
- **GitHub**: https://github.com/vkbo/novelWriter
- **Stars**: 2.4k | **语言**: Python (PyQt5)
- **核心**: 纯文本存储+树形项目结构+角色/地点管理+写作进度
- **借鉴**: 纯文本优先的元数据设计；树形"根→章→场景">线性编辑

---

## 对 novel_any 的增强映射

| 现有模块 | 借鉴项目 | 增强方向 |
|---------|---------|---------|
| **stats** | lexical_diversity, textstat | MTLD/HD-D 替代 TTR；章节级可读性曲线 |
| **slop** | GLTR, HC3 | Token rank 分布；语言学特征 AI 检测 |
| **bible** | BookNLP, HarvestText | 人物名聚类/实体链接；出场频率/POV 追踪 |
| **consistency** | SentimentArcs, BookNLP | 多模型情感曲线+六弧线分类；超语义标注 |
| **outline** | SnowNLP, HarvestText | TextRank 摘要 diff；TextTiling 自动分段 |
| **🆕 style_lint** | proselint, write-good | 模块化中文写作规范检查器 |
