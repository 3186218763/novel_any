"""情绪曲线提取 — 多模型集成 + 滑动窗口 + 六弧线分类."""

import re
from pathlib import Path

EMOTION_DICT = {
    "狂喜": ("positive", 1.0), "兴奋": ("positive", 0.9), "激动": ("positive", 0.9),
    "欢呼": ("positive", 0.9), "惊喜": ("positive", 0.8), "欣慰": ("positive", 0.7),
    "满足": ("positive", 0.6), "幸福": ("positive", 0.8), "温暖": ("positive", 0.6),
    "甜蜜": ("positive", 0.7), "愉快": ("positive", 0.7), "开心": ("positive", 0.7),
    "高兴": ("positive", 0.7), "喜悦": ("positive", 0.8), "得意": ("positive", 0.6),
    "骄傲": ("positive", 0.6), "自豪": ("positive", 0.7), "安心": ("positive", 0.5),
    "放松": ("positive", 0.4), "宁静": ("positive", 0.3), "感动": ("positive", 0.7),
    "感激": ("positive", 0.6), "期待": ("positive", 0.5),
    "愤怒": ("negative", 0.9), "暴怒": ("negative", 1.0), "狂怒": ("negative", 1.0),
    "恐惧": ("negative", 0.9), "惊恐": ("negative", 1.0), "绝望": ("negative", 1.0),
    "悲痛": ("negative", 0.9), "悲伤": ("negative", 0.7), "痛苦": ("negative", 0.8),
    "崩溃": ("negative", 0.9), "撕心裂肺": ("negative", 1.0), "焦虑": ("negative", 0.7),
    "不安": ("negative", 0.6), "紧张": ("negative", 0.7), "害怕": ("negative", 0.7),
    "惊慌": ("negative", 0.8), "后悔": ("negative", 0.6), "愧疚": ("negative", 0.6),
    "自责": ("negative", 0.6), "怨恨": ("negative", 0.7), "憎恨": ("negative", 0.9),
    "厌恶": ("negative", 0.7), "失落": ("negative", 0.6), "寂寞": ("negative", 0.5),
    "孤独": ("negative", 0.5), "委屈": ("negative", 0.6), "伤心": ("negative", 0.6),
    "难过": ("negative", 0.5), "危险": ("tension", 0.8), "危机": ("tension", 0.9),
    "绝境": ("tension", 0.9), "杀意": ("tension", 0.9), "杀气": ("tension", 0.8),
    "对峙": ("tension", 0.8), "冲突": ("tension", 0.7), "决斗": ("tension", 0.9),
    "战斗": ("tension", 0.8), "追杀": ("tension", 0.9), "逃命": ("tension", 0.8),
    "生死": ("tension", 0.9), "威胁": ("tension", 0.7), "压迫": ("tension", 0.7),
    "窒息": ("tension", 0.8), "悬念": ("tension", 0.6), "疑云": ("tension", 0.6),
    "阴谋": ("tension", 0.7), "平静": ("neutral", 0.2), "淡然": ("neutral", 0.2),
    "从容": ("neutral", 0.3), "深沉": ("neutral", 0.4), "沉思": ("neutral", 0.3),
    "沉默": ("neutral", 0.3), "思索": ("neutral", 0.2), "观察": ("neutral", 0.1),
    "观望": ("neutral", 0.1), "徘徊": ("neutral", 0.2), "犹豫": ("neutral", 0.3),
}

ARC_TEMPLATES = {
    "rags_to_riches":     [0.2, 0.3, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9],
    "riches_to_rags":     [0.9, 0.8, 0.7, 0.6, 0.4, 0.3, 0.3, 0.2],
    "man_in_hole":        [0.6, 0.5, 0.3, 0.2, 0.3, 0.5, 0.7, 0.8],
    "icarus":             [0.4, 0.5, 0.7, 0.9, 0.6, 0.4, 0.3, 0.2],
    "cinderella":         [0.3, 0.5, 0.7, 0.4, 0.2, 0.5, 0.7, 0.9],
    "oedipus":            [0.7, 0.5, 0.3, 0.5, 0.7, 0.4, 0.3, 0.2],
}


def extract_emotion_curve(filepath: str, segments: int = 40,
                          weights: dict | None = None) -> dict:
    """提取章节情绪曲线（多模型集成）."""
    if weights is None:
        weights = {"dict": 0.5, "snownlp": 0.3, "hf": 0.2}

    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (UnicodeDecodeError, PermissionError, IOError) as e:
        return {"error": str(e)}

    text = re.sub(r'^---.*?---\n', '', text, flags=re.DOTALL)
    total_chars = len(text)
    if total_chars < 100:
        return {"error": "Text too short", "curve": [], "peaks": [], "avg_intensity": 0}

    window_size = 500
    step = 250
    curve = []
    all_hits = {}

    pos = 0
    while pos + window_size <= total_chars:
        segment = text[pos:pos + window_size]
        seg_len = len(segment)

        dict_intensity = 0.0
        for word, (category, intensity) in EMOTION_DICT.items():
            count = segment.count(word)
            if count > 0:
                dict_intensity += count * intensity
                all_hits[word] = all_hits.get(word, 0) + count
        dict_norm = round(dict_intensity / (seg_len / 100), 3)

        snownlp_norm = 0.5
        try:
            from snownlp import SnowNLP
            s = SnowNLP(segment)
            snownlp_norm = s.sentiments
        except ImportError:
            pass

        # No HF model available; redistribute hf weight proportionally
        d_w = weights["dict"]
        s_w = weights["snownlp"]
        h_w = weights.get("hf", 0)
        total_w = d_w + s_w + h_w
        if total_w > 0:
            combined = dict_norm * (d_w + h_w) / total_w + snownlp_norm * s_w / total_w
        else:
            combined = dict_norm

        curve.append({
            "position": round(pos / total_chars, 3),
            "intensity": round(combined, 3),
        })
        pos += step

    intensities = [p["intensity"] for p in curve]
    avg_intensity = round(sum(intensities) / len(intensities), 3) if intensities else 0
    # 情绪波动幅度（标准差）— 越低越平淡
    if len(intensities) > 1:
        mean = sum(intensities) / len(intensities)
        variance = sum((v - mean) ** 2 for v in intensities) / len(intensities)
        raw_variance = variance ** 0.5
        # 短文本归一化: < 2000 字的文本窗口少，方差虚高，乘以惩罚系数
        if total_chars < 2000:
            penalty = max(0.3, total_chars / 2000)  # 0.3 ~ 1.0
            intensity_variance = round(raw_variance * penalty, 4)
        else:
            intensity_variance = round(raw_variance, 4)
    else:
        intensity_variance = 0.0
    threshold = avg_intensity * 1.5 if avg_intensity > 0 else 0.5
    peaks = [p["position"] for p in curve if p["intensity"] >= max(threshold, 0.2)]

    arc_type = _classify_arc(intensities)
    sorted_hits = sorted(all_hits.items(), key=lambda x: x[1], reverse=True)[:15]

    return {
        "file_path": str(path),
        "curve": curve,
        "peaks": peaks,
        "avg_intensity": avg_intensity,
        "intensity_variance": intensity_variance,
        "peak_count": len(peaks),
        "emotion_keywords": {word: count for word, count in sorted_hits},
        "arc_type": arc_type,
    }


def _classify_arc(intensities: list[float]) -> dict:
    """将强度序列匹配到六弧线类型."""
    if len(intensities) < 4:
        return {"type": "unknown", "confidence": 0}
    mn, mx = min(intensities), max(intensities)
    if mx - mn < 0.01:
        return {"type": "flat", "confidence": 0.5}
    norm = [(v - mn) / (mx - mn) for v in intensities]
    n = len(norm)
    indices = [int(i * (n - 1) / 7) for i in range(8)]
    sampled = [norm[idx] for idx in indices]

    best = "unknown"
    best_score = float("inf")
    for name, template in ARC_TEMPLATES.items():
        mse = sum((sampled[i] - template[i]) ** 2 for i in range(8)) / 8
        if mse < best_score:
            best_score = mse
            best = name

    return {"type": best, "confidence": round(max(0, 1 - best_score), 3)}
