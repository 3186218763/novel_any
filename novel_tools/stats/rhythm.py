"""情绪曲线提取 — 基于关键词密度，按段落输出情绪强度."""

import re
from pathlib import Path

# 情绪词典：词 → (类别, 强度 0-1)
EMOTION_DICT = {
    # 强烈正面
    "狂喜": ("positive", 1.0), "兴奋": ("positive", 0.9), "激动": ("positive", 0.9),
    "欢呼": ("positive", 0.9), "雀跃": ("positive", 0.8), "惊喜": ("positive", 0.8),
    "欣慰": ("positive", 0.7), "满足": ("positive", 0.6), "幸福": ("positive", 0.8),
    "温暖": ("positive", 0.6), "甜蜜": ("positive", 0.7), "愉快": ("positive", 0.7),
    "开心": ("positive", 0.7), "高兴": ("positive", 0.7), "喜悦": ("positive", 0.8),
    "得意": ("positive", 0.6), "骄傲": ("positive", 0.6), "自豪": ("positive", 0.7),
    "安心": ("positive", 0.5), "放松": ("positive", 0.4), "宁静": ("positive", 0.3),
    "感动": ("positive", 0.7), "感激": ("positive", 0.6), "期待": ("positive", 0.5),

    # 强烈负面
    "愤怒": ("negative", 0.9), "暴怒": ("negative", 1.0), "狂怒": ("negative", 1.0),
    "恐惧": ("negative", 0.9), "惊恐": ("negative", 1.0), "绝望": ("negative", 1.0),
    "悲痛": ("negative", 0.9), "悲伤": ("negative", 0.7), "痛苦": ("negative", 0.8),
    "崩溃": ("negative", 0.9), "撕心裂肺": ("negative", 1.0), "肝肠寸断": ("negative", 0.9),
    "焦虑": ("negative", 0.7), "不安": ("negative", 0.6), "紧张": ("negative", 0.7),
    "恐惧": ("negative", 0.9), "害怕": ("negative", 0.7), "惊慌": ("negative", 0.8),
    "后悔": ("negative", 0.6), "愧疚": ("negative", 0.6), "自责": ("negative", 0.6),
    "怨恨": ("negative", 0.7), "憎恨": ("negative", 0.9), "厌恶": ("negative", 0.7),
    "失落": ("negative", 0.6), "寂寞": ("negative", 0.5), "孤独": ("negative", 0.5),
    "委屈": ("negative", 0.6), "伤心": ("negative", 0.6), "难过": ("negative", 0.5),

    # 紧张/冲突
    "危险": ("tension", 0.8), "危机": ("tension", 0.9), "绝境": ("tension", 0.9),
    "杀意": ("tension", 0.9), "杀气": ("tension", 0.8), "对峙": ("tension", 0.8),
    "冲突": ("tension", 0.7), "决斗": ("tension", 0.9), "战斗": ("tension", 0.8),
    "追杀": ("tension", 0.9), "逃命": ("tension", 0.8), "生死": ("tension", 0.9),
    "威胁": ("tension", 0.7), "压迫": ("tension", 0.7), "窒息": ("tension", 0.8),
    "悬念": ("tension", 0.6), "疑云": ("tension", 0.6), "阴谋": ("tension", 0.7),

    # 平和/中性
    "平静": ("neutral", 0.2), "淡然": ("neutral", 0.2), "从容": ("neutral", 0.3),
    "平静": ("neutral", 0.2), "深沉": ("neutral", 0.4), "沉思": ("neutral", 0.3),
    "沉默": ("neutral", 0.3), "思索": ("neutral", 0.2), "观察": ("neutral", 0.1),
    "观望": ("neutral", 0.1), "徘徊": ("neutral", 0.2), "犹豫": ("neutral", 0.3),
}


def extract_emotion_curve(filepath: str, segments: int = 40) -> dict:
    """提取章节情绪曲线.

    将文本等分为 N 段，每段统计情绪词命中数 × 强度。

    Args:
        filepath: 章节路径
        segments: 等分段数（默认 40）

    Returns:
        dict with: curve, peaks, avg_intensity, emotion_keywords
    """
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    with open(path, encoding="utf-8") as f:
        text = f.read()

    # 移除 frontmatter
    text = re.sub(r'^---.*?---\n', '', text, flags=re.DOTALL)

    total_chars = len(text)
    if total_chars < 100:
        return {"error": "Text too short", "curve": [], "peaks": [], "avg_intensity": 0}

    # 等分文本
    seg_size = max(total_chars // segments, 1)
    curve = []
    all_hits = {}

    for i in range(segments):
        start = i * seg_size
        end = min(start + seg_size, total_chars) if i < segments - 1 else total_chars
        segment = text[start:end]
        seg_len = end - start

        # 统计每段的情绪强度
        total_intensity = 0.0
        for word, (category, intensity) in EMOTION_DICT.items():
            count = segment.count(word)
            if count > 0:
                total_intensity += count * intensity
                all_hits[word] = all_hits.get(word, 0) + count

        # 归一化（每 100 字）
        norm_intensity = round(min(total_intensity / (seg_len / 100), 3.0), 3) if seg_len > 0 else 0
        curve.append({
            "position": round(i / segments, 3),
            "intensity": norm_intensity,
        })

    # 找波峰（高于均值 1.5 倍）
    intensities = [p["intensity"] for p in curve]
    avg_intensity = round(sum(intensities) / len(intensities), 3) if intensities else 0
    threshold = avg_intensity * 1.5 if avg_intensity > 0 else 0.5
    peaks = [p["position"] for p in curve if p["intensity"] >= threshold and p["intensity"] > 0.2]

    # 情绪词频 Top 15
    sorted_hits = sorted(all_hits.items(), key=lambda x: x[1], reverse=True)[:15]

    return {
        "file_path": str(path),
        "curve": curve,
        "peaks": peaks,
        "avg_intensity": avg_intensity,
        "peak_count": len(peaks),
        "emotion_keywords": {word: count for word, count in sorted_hits},
    }
