"""重复句式/滥用词扫描 — 句首重复、段落开头重复、高频副词."""

import re
from collections import Counter
from pathlib import Path


def scan_repetition(text: str) -> dict:
    """扫描重复句式和段落开头.

    Returns:
        dict with repeated_phrases, sentence_starts, paragraph_starts
    """
    # 句子分割
    sentences = [s.strip() for s in re.split(r'[。！？…]+', text) if s.strip() and len(s.strip()) > 3]

    # 1. 句首 2-3 字统计
    starts_2 = Counter()
    starts_3 = Counter()
    for s in sentences:
        if len(s) >= 2:
            starts_2[s[:2]] += 1
        if len(s) >= 3:
            starts_3[s[:3]] += 1

    # 只保留出现 >= 3 次的
    repeated_2 = [(p, c) for p, c in starts_2.most_common(20) if c >= 3]
    repeated_3 = [(p, c) for p, c in starts_3.most_common(20) if c >= 3]

    # 2. 段落开头统计
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip() and len(p.strip()) > 5]
    para_starts = Counter()
    for p in paragraphs:
        first_sentence = re.split(r'[。！？…]', p)[0].strip()
        if len(first_sentence) >= 3:
            para_starts[first_sentence[:4]] += 1

    repeated_para = [(p, c) for p, c in para_starts.most_common(15) if c >= 2]

    # 3. 3-5 字短语重复（滑动窗口，采样上限防内存爆炸）
    words = list(re.findall(r'[\u4e00-\u9fff]+', text))
    # 限制分析的文本量：最多取前 20000 个中文字符的连续片段
    MAX_TEXT_LEN = 20000
    char_count = 0
    limited_words = []
    for w in words:
        limited_words.append(w)
        char_count += len(w)
        if char_count >= MAX_TEXT_LEN:
            break
    # 限制短语总数上限
    MAX_PHRASES = 5000
    phrases = Counter()
    for w in limited_words:
        if len(w) >= 3:
            for n in range(3, min(6, len(w) + 1)):
                for i in range(len(w) - n + 1):
                    phrase = w[i:i + n]
                    phrases[phrase] += 1
                    if len(phrases) >= MAX_PHRASES:
                        break
                if len(phrases) >= MAX_PHRASES:
                    break
        if len(phrases) >= MAX_PHRASES:
            break

    repeated_phrases = [(p, c) for p, c in phrases.most_common(30) if c >= 3]

    return {
        "sentence_starts_2char": [{"phrase": p, "count": c} for p, c in repeated_2],
        "sentence_starts_3char": [{"phrase": p, "count": c} for p, c in repeated_3],
        "paragraph_starts": [{"phrase": p, "count": c} for p, c in repeated_para],
        "repeated_phrases": [{"phrase": p, "count": c} for p, c in repeated_phrases[:20]],
        "total_repeated_phrase_types": len(repeated_phrases),
    }


def scan_overused(text: str) -> dict:
    """扫描滥用词（高频副词、连接词、语气词）.

    Returns:
        dict with words list and suggestions
    """
    # 常见滥用词列表
    OVERUSED_PATTERNS = [
        # 高频副词
        "就", "都", "很", "非常", "一直", "总是", "已经", "立刻", "马上", "忽然",
        "突然", "渐渐", "慢慢", "轻轻", "默默", "淡淡", "微微", "略略",
        # 连接词
        "然而", "但是", "不过", "而且", "因此", "所以", "于是", "然后", "接着",
        # 语气词
        "吧", "呢", "啊", "哦", "嗯", "嘛", "啦",
        # 修饰词
        "似乎", "仿佛", "好像", "也许", "大概", "可能", "应该", "竟然", "居然",
    ]

    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text)) or 1
    results = []

    for word in OVERUSED_PATTERNS:
        count = text.count(word)
        per_1k = round(count / (chinese_chars / 1000), 2) if chinese_chars > 0 else 0
        if per_1k > 2.0:  # 每千字超过 2 次视为滥用
            results.append({
                "word": word,
                "count": count,
                "per_1k": per_1k,
            })

    results.sort(key=lambda x: x["per_1k"], reverse=True)

    # 生成建议
    suggestions = []
    if results:
        top_words = [r["word"] for r in results[:5]]
        suggestions.append(f"高频词: {'、'.join(top_words)}。建议替换或删减部分。")
        suggestions.append("可尝试变换句式，避免重复使用相同副词开头。")

    return {
        "overused_count": len(results),
        "words": results[:20],
        "suggestions": suggestions,
    }
