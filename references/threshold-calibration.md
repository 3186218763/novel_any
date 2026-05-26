# 工具阈值校准方法论

> 基于 2026-05-26 对 novel_tools 6 个模块的大规模验证（13 本书, 512 章, 31 条评论）

## 校准流程

```
1. 抓取真实小说 + 评论
2. 运行工具分析 → 生成指标
3. 评论维度提取 → 映射到工具模块
4. 对比: tool claim vs reviewer claim → matched / false_neg / false_pos
5. 分析 gap 根因 → 调整阈值或新增检测
6. 重新验证 → 观察 matched rate 变化
7. 重复直到平台期
```

## 本次校准记录

| Round | matched | gaps | 修复项 |
|-------|---------|------|--------|
| init  | 3.8%    | 113  | — |
| R1    | 30.2%   | 73   | 路径修复(summary.total/action_density) + 短语重复 + pacing复合 |
| R2    | 49.7%   | 51   | intensity_variance + gte/lte + 自适应阈值 + 否定检测 |
| R3    | 61.6%   | 37   | quick_scan + 方差归一化 |
| R4    | 61.6%   | 37   | 平台期 — 短文本理论上限 |

## 关键阈值

```python
_TOOL_THRESHOLDS = {
    "pacing":         {"metric": "action_density",     "op": "lt",  "value": 15},    # 原始 0.4→15
    "readability":    {"metric": "readability.flesch_zh", "op": "lt", "value": 30},
    "emotion_arc":    {"metric": "intensity_variance", "op": "lt",  "value": 0.08},  # 从 avg_intensity 切换
    "redundancy":     {"metric": "summary.total",       "op": "gte", "value": 1},    # 从 gt 5 切换
    "ai_score":       {"metric": "total_score",         "op": "gt",  "value": 20},   # 原始 50→25→20
    "template_score": {"metric": "template_score",      "op": "gt",  "value": 30},
}
```

## 特殊处理

- **pacing 复合检测**: action_density < 15 OR narration_ratio > 0.75 = slow pacing（水文检测）
- **redundancy 自适应**: 短文本(<2000字) threshold=0, 长文本 threshold=1
- **emotion 短文本归一化**: intensity_variance *= max(0.3, total_chars/2000)，补偿少窗口虚高
- **否定检测**: "少了老套" → positive（非 negative），negation_words = ["少了","没有","不是","避免"...]

## 已知局限

1. **1079 字预览片段**：所有 biquge 盗版站统一限制，完整章节需 trxs.cc + Playwright
2. **同人小说无豆瓣条目**：trxs.cc 的章节虽长但无法匹配评论
3. **"模板化"需跨章检测**：读者感知的模板模式（如"每次升级都是同一种套路"）单章词级工具无法捕获
4. **评论覆盖率**：仅 5/13 书匹配到豆瓣评论，贴吧未充分启用
