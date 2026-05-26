# 工具验证模式

## 闭环流程

```
抓取小说 → 全模块分析 → 豆瓣评论抓取 → 维度对比验证 → 发现 gap → 修复工具 → 重跑确认
```

## 验证维度映射

| 评论关键词 | 工具维度 | 对应模块 | 阈值 |
|-----------|---------|---------|------|
| 节奏慢/拖/水文 | pacing | action_density | <15 |
| 角色崩/人设 | character_consistency | names | - |
| AI写/套路/模板 | ai_score + template_score | total_score / cross_chapter | >20 / >30 |
| 读不下去/太绕 | readability | readability.flesch_zh | <30 |
| 情绪平/没起伏 | emotion_arc | intensity_variance | <0.08 |
| 啰嗦/废话多 | redundancy | summary.total | >5 (>1 for short text) |

## 阈值校准方法

1. 取 10+ 本书的大规模验证数据
2. 对每个模块，统计评论触发该维度的章节的指标值分布
3. 选 P25 作为初始阈值（25% 的"差"章节低于此值）
4. 跑验证确认 matched 率
5. 根据 false_negative / false_positive 比例调优

## v0.3.0 校准结果

| 模块 | 初始阈值 | 校准后 | matched率变化 |
|------|---------|--------|-------------|
| pacing | 0.4 (错) | 15 + narration_ratio>0.75 | 0 gap |
| ai_score | 50 | 20 | gap从38降到17 |
| emotion | avg_intensity 0.3 | intensity_variance 0.08 | gap从35降到22 |
| redundancy | gt 5 | gte 1 (自适应) | gap从40降到29 |

## 常见陷阱

1. **指标值域误判**: `action_density` 是每千字动作数(~10-50)，非0-1比例
2. **嵌套路径**: `flesch_zh` 在 `readability.flesch_zh` 下，`total_issues` 不存在(int是`summary.total`)
3. **字段为空**: `risk.score` 始终为空dict，应用 `total_score`
4. **book-level分析**: `cross_chapter` 存 `chapter_id=0`，验证时需特殊处理
5. **否定检测**: "少了老套"不是抱怨，需检查前5字否定词
6. **短文本**: 1079字片段style_lint永远0 issue，自适应阈值也救不了

## 已知局限（v0.3.0）

- 所有笔趣阁镜像站返回章节预览片段（~1079字），非完整内容
- style_lint 和 emotion 在短文本上精度受限
- cross_chapter 模板检测基于统计特征，无法识别语义级套路
- 豆瓣评论覆盖率 ~40%（大量网文书无豆瓣条目）
