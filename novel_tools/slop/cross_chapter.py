"""跨章结构模式检测 — 检测模板化写作."""

import re
from collections import Counter


def detect_template_patterns(chapters: list[str]) -> dict:
    """检测多章间重复的叙事结构模式.
    
    Args:
        chapters: 章节文本列表，按顺序排列
    
    Returns:
        dict with template_score and detected patterns
    """
    if len(chapters) < 2:
        return {"template_score": 0, "repeated_openings": 0, "length_cv": 0, "opening_patterns": []}
    
    # 1. 章节开头模式重复检测（前20字）
    opening_patterns = Counter()
    for text in chapters:
        chars = re.findall(r'[\u4e00-\u9fff]', text)
        if len(chars) >= 8:
            opening = ''.join(chars[:8])
            opening_patterns[opening] += 1
    
    # 2. 章节长度分布（变异系数越小越模板化）
    lengths = [len(text) for text in chapters if text]
    if len(lengths) > 1:
        mean_l = sum(lengths) / len(lengths)
        std_l = (sum((l - mean_l) ** 2 for l in lengths) / len(lengths)) ** 0.5
        length_cv = round(std_l / mean_l, 3) if mean_l > 0 else 0
    else:
        length_cv = 0
    
    # 3. 叙事节奏一致性（对话比例、动作密度的跨章方差）
    dialogue_ratios = []
    for text in chapters:
        dl = len(re.findall(r'[「""][^」""]+[」""]', text))
        total = len(re.findall(r'[\u4e00-\u9fff]', text)) or 1
        dialogue_ratios.append(dl / max(total / 100, 1))
    
    dl_cv = 0
    if len(dialogue_ratios) > 1 and sum(dialogue_ratios) > 0:
        dl_mean = sum(dialogue_ratios) / len(dialogue_ratios)
        dl_std = (sum((d - dl_mean) ** 2 for d in dialogue_ratios) / len(dialogue_ratios)) ** 0.5
        dl_cv = round(dl_std / dl_mean, 3) if dl_mean > 0 else 0
    
    # 4. 评分
    repeated_openings = sum(1 for c in opening_patterns.values() if c >= 2)
    template_score = min(repeated_openings * 15 + max(0, int((0.3 - min(length_cv, 0.3)) * 100)) + max(0, int((0.3 - min(dl_cv, 0.3)) * 80)), 100)
    
    return {
        "template_score": round(template_score),
        "repeated_openings": repeated_openings,
        "length_cv": length_cv,
        "dialogue_cv": dl_cv,
        "opening_patterns": [(p, c) for p, c in opening_patterns.most_common(5) if c >= 2],
    }
