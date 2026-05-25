"""AI 文本特征分析器 — TTR、句长变异、结构模式、重复度."""

import math
import re
from dataclasses import dataclass, field


# 中文句子分割
_SENTENCE_SPLIT = re.compile(r'[。！？…]+')

# AI 典型结构模式
_STRUCTURE_PATTERNS = {
    "first_second_last": re.compile(
        r'(?:首先|第一|其一).{3,}?(?:其次|第二|其二).{3,}?(?:再次|第三|其三|最后)'
    ),
    "total_sub_total": re.compile(r".{8,}?[：:].{15,}?(?:总之|综上|总而言之|由此可见)"),
    "not_only_but_also": re.compile(r"不仅.{2,}?而且"),
    "not_x_but_y": re.compile(r"不是.{2,}?而是"),
    "on_one_hand": re.compile(r"一方面.{3,}?另一方面"),
    "although_but": re.compile(r"(?:虽然|尽管).{2,}?(?:但是|然而|却)"),
    "because_so": re.compile(r"因为.{2,}?所以"),
    "moreover": re.compile(r"(?:此外|另外|除此之外).{3,}?(?:也|还|更)"),
    "in_short": re.compile(r"(?:总而言之|综上所述|简而言之|一言以蔽之)"),
}


def split_sentences(text: str) -> list[str]:
    """将文本分割为句子列表."""
    parts = _SENTENCE_SPLIT.split(text.strip())
    return [s.strip() for s in parts if s.strip() and len(s.strip()) > 1]


def calc_ttr(words: list[str]) -> float:
    """Type-Token Ratio（词汇多样性）."""
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def calc_hapax_ratio(words: list[str]) -> float:
    """只出现一次的词占比."""
    if not words:
        return 0.0
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    hapax = sum(1 for v in freq.values() if v == 1)
    return hapax / len(words)


def calc_sentence_variance(sentences: list[str]) -> tuple[float, float]:
    """句子长度变异系数 (avg_len, cv)."""
    if len(sentences) < 2:
        return (len(sentences[0]) if sentences else 0, 0.0)
    lengths = [len(s) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return (0.0, 0.0)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    cv = math.sqrt(variance) / mean
    return (mean, cv)


def detect_structure_patterns(text: str) -> list[str]:
    """检测 AI 典型结构模式."""
    return [name for name, pattern in _STRUCTURE_PATTERNS.items() if pattern.search(text)]


def calc_repetition_score(sentences: list[str]) -> float:
    """相邻句子结构相似度（高=AI特征）."""
    if len(sentences) < 2:
        return 0.0
    similarities = []
    for i in range(len(sentences) - 1):
        s1, s2 = sentences[i], sentences[i + 1]
        len1, len2 = len(s1), len(s2)
        if max(len1, len2) == 0:
            continue
        len_sim = min(len1, len2) / max(len1, len2)
        # 简化版：只比长度相似度
        similarities.append(len_sim)
    return round(sum(similarities) / len(similarities), 3) if similarities else 0.0


def analyze_text(text: str) -> dict:
    """全维度 AI 特征分析.

    Returns:
        dict with ttr, hapax_ratio, sentence_count, avg_sentence_len,
        sentence_len_cv, blacklist_hits, blacklist_density,
        structure_patterns, repetition_score
    """
    # 分词
    try:
        import jieba
        words = list(jieba.cut(text))
        words = [w.strip() for w in words if w.strip() and re.search(r'[\u4e00-\u9fff]', w)]
    except ImportError:
        # 简单按字拆分
        words = list(re.findall(r'[\u4e00-\u9fff]', text))

    # 句子分析
    sentences = split_sentences(text)

    # TTR
    ttr = round(calc_ttr(words), 3)
    hapax = round(calc_hapax_ratio(words), 3)

    # 句长变异
    avg_sl, sl_cv = calc_sentence_variance(sentences)

    # 结构模式
    structure = detect_structure_patterns(text)

    # 重复度
    rep_score = calc_repetition_score(sentences)

    # 黑名单检查
    from novel_tools.slop.dictionary import load_dictionary
    slop_dict = load_dictionary()
    hits = slop_dict.count_hits(text)
    total_hits = sum(hits.values())
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text)) or 1
    bl_density = round(total_hits / (chinese_chars / 100), 1)  # 每百字命中数

    return {
        "ttr": ttr,
        "hapax_ratio": hapax,
        "word_count": len(words),
        "sentence_count": len(sentences),
        "avg_sentence_len": round(avg_sl, 1),
        "sentence_len_cv": round(sl_cv, 3),
        "blacklist_total_hits": total_hits,
        "blacklist_density": bl_density,
        "blacklist_hits": dict(sorted(hits.items(), key=lambda x: x[1], reverse=True)[:20]),
        "structure_patterns": structure,
        "structure_pattern_count": len(structure),
        "repetition_score": rep_score,
    }


def score_ai_risk(metrics: dict) -> dict:
    """将指标转化为 AI 风险评分 (0-100).

    评分逻辑:
    - TTR 低 → 高分（AI 特征）
    - 句长变异低 → 高分（AI 特征）
    - 结构模式多 → 高分
    - 黑名单密度高 → 高分
    - 重复度高分 → 高分
    """
    scores = {}

    # TTR: < 0.35 → 高风险，> 0.6 → 低风险
    ttr = metrics.get("ttr", 0.5)
    scores["ttr"] = max(0, min(100, int((0.6 - ttr) * 250)))

    # 句长变异: < 0.3 → AI，> 0.7 → 人
    cv = metrics.get("sentence_len_cv", 0.5)
    scores["sentence_variance"] = max(0, min(100, int((0.7 - cv) * 250)))

    # 结构模式: 每个 20 分
    sp_count = metrics.get("structure_pattern_count", 0)
    scores["structure"] = min(100, sp_count * 20)

    # 黑名单密度: 每百字 > 5 个 → 高风险
    bl_density = metrics.get("blacklist_density", 0)
    scores["blacklist"] = min(100, int(bl_density * 15))

    # 重复度: > 0.6 → AI
    rep = metrics.get("repetition_score", 0)
    scores["repetition"] = max(0, min(100, int((rep - 0.3) * 250)))

    # 加权合成
    weights = {"ttr": 0.25, "sentence_variance": 0.20, "structure": 0.15, "blacklist": 0.25, "repetition": 0.15}
    total = sum(scores[k] * weights[k] for k in weights)

    if total < 30:
        verdict = "低风险 — 文字自然，AI 特征不明显"
    elif total < 60:
        verdict = "中风险 — 部分维度偏高，建议针对性调整"
    else:
        verdict = "高风险 — 多处 AI 特征明显，需要深度修改"

    return {
        "total_score": round(total),
        "breakdown": scores,
        "verdict": verdict,
    }
