# novel_tools 验证方法论

验证 novel_tools 各模块准确性的标准流程。

## 流程

```
1. 抓取 15 本不同类型小说 × 40 章
2. 运行全模块分析 → 存储到 pipeline.db
3. 从豆瓣抓取读者评论（需要代理）
4. 验证器将评论关键词映射到工具维度，逐章对比
5. 发现 gap → 分析根因 → 修工具 → 重跑验证 → 迭代
```

## 维度映射表

| 评论关键词 | 映射维度 | 对应模块 | 说明 |
|-----------|---------|---------|------|
| 节奏慢/拖/水文 | pacing | pacing | 检测 action_density + narration_ratio |
| 角色崩/人设 | character_consistency | stats | 未完成 |
| AI/模板/套路/老套 | ai_score / template_score | slop / cross_chapter | "老套""套路"→template_score(跨章)，"模板"→ai_score |
| 读不下去/太绕 | readability | stats | flesch_zh |
| 情绪平/没起伏/平淡 | emotion_arc | consistency | intensity_variance |
| 啰嗦/废话/冗余 | redundancy | style_lint | summary.total |

## 阈值迭代记录

v0.3.0 在 13 本书 512 章 31 条评论上校准：

| 轮次 | matched | gaps | 关键修复 |
|------|---------|------|---------|
| 初始 | 3.8% | 113 | - |
| R1 | 30.2% | 73 | 路径修复(summary.total/avg_intensity→intensity_variance) + pacing 复合检测(narration_ratio) + 短语重复融入 ai_score |
| R2 | 49.7% | 51 | gte/lte 操作符 + 自适应阈值(短文本<2000字=1) + 关键词否定检测 + book-level 分析回退 |
| R3 | 61.6% | 37 | quick_scan 短文本启发式 + emotion 方差长度归一化 |
| R4 | 61.6% | 37 | 平台期 — 1079 字预览片段的理论上限 |

## 已校准阈值

| 维度 | 指标 | 操作符 | 阈值 | 依据 |
|------|------|--------|------|------|
| pacing | action_density | lt | 15 | 值域 ~10-50(每千字动作元素数)，低于 15 表示节奏慢 |
| pacing(水文) | narration_ratio | gt | 0.75 | 高叙述占比 = 缺乏对话/动作驱动 |
| readability | readability.flesch_zh | lt | 30 | 中文可读性标准阈值 |
| ai_score | total_score | gt | 20 | 包含 phrase_repetition_score 加权 |
| template_score | template_score | gt | 30 | 跨章分析，存储为 chapter_id=0 |
| emotion | intensity_variance | lt | 0.08 | 情绪曲线标准差，短文本归一化(×total_chars/2000) |
| redundancy | summary.total | gte | 1(短)/5(长) | 短文本(<2000字)自适应降为 1 |

## 关键词否定检测

验证器 `_extract_dimensions_simple` 在匹配关键词后需检查前 5 字是否有否定词：

```
否定词列表: ["少了", "没有", "不是", "避免", "不像", "没什么", "毫无", "不"]
```

检测到否定词 → sentiment 翻转(negative↔positive)。
例如: "它少了很多老套剧情" → "老套"匹配到 negative → 前缀"少了"是否定 → 翻转为 positive

## 短文本局限

所有笔趣阁镜像站统一返回 ~1000 字预览片段。影响：
- style_lint: 模式规则难以触发，quick_scan(副词密度/句首重复/感叹号密度/叠词)作为补充
- emotion: 窗口数少(仅 2-3 个)，方差虚高，需惩罚系数归一化
- ai_score: 统计指标(TTR/句长变异)在小样本上不准确

突破 61.6% 需完整章节(3000+字)。
