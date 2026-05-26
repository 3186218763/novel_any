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



# 中文弱化词/陈词规则（借鉴 proselint write-good）
_WEASEL_PATTERNS = {
    "weasel": [
        "众所周知", "不言而喻", "值得注意的是", "显而易见",
        "毫无疑问", "毋庸置疑", "不可否认", "必须承认",
        "总的来说", "综上所述", "总而言之",
    ],
    "hedge": [
        "某种程度上", "某种意义上", "相对而言", "一般来说",
        "在某种程度上", "在很大程度上", "大体上",
        "似乎", "仿佛", "好像", "也许", "可能", "大概",
    ],
    "cliche_structure": [
        r"令人[\u4e00-\u9fff]{1,3}",
        r"让人[\u4e00-\u9fff]{1,3}",
        r"使人[\u4e00-\u9fff]{1,3}",
        r"[\u4e00-\u9fff]{1,2}地说",
        r"[\u4e00-\u9fff]{1,2}地道",
    ],
}


def scan_chinese_weasel(text: str) -> dict:
    """扫描中文弱化词/陈词."""
    results: dict[str, list[dict]] = {"weasel": [], "hedge": [], "cliche_structure": []}
    total = 0

    for category, patterns in _WEASEL_PATTERNS.items():
        for pattern in patterns:
            if any(pattern.startswith(p) for p in ["令", "让", "使"]) or \
               any(pattern.endswith(p) for p in ["说", "道"]):
                for m in re.finditer(pattern, text):
                    results[category].append({
                        "text": m.group(0),
                        "position": m.start(),
                    })
                    total += 1
            else:
                count = text.count(pattern)
                if count > 0:
                    for _ in range(count):
                        results[category].append({"text": pattern, "position": -1})
                        total += 1

    for cat in results:
        seen = set()
        deduped = []
        for d in results[cat]:
            key = (d["text"], d["position"])
            if key not in seen:
                seen.add(key)
                deduped.append(d)
        results[cat] = deduped

    return {
        "total_hits": sum(len(v) for v in results.values()),
        "by_category": results,
    }


def scan_phrase_repetition(text: str, min_len: int = 3, min_count: int = 3) -> dict:
    """扫描文本中重复出现的短语——检测模板化描写（如\"惊才绝艳\"用了N次）.

    Returns:
        dict with repeated_phrases list and total_repetition_score.
    """
    from collections import Counter

    # 提取所有中文片段
    chars = re.findall(r"[\u4e00-\u9fff]+", text)
    full_text = "".join(chars)

    phrase_counter: Counter = Counter()
    # 滑动窗口：2-5 字短语
    for l in range(min_len, 6):
        for i in range(len(full_text) - l + 1):
            phrase = full_text[i : i + l]
            phrase_counter[phrase] += 1

    # 过滤掉单字符和只出现 1-2 次的
    repeated = [(p, c) for p, c in phrase_counter.most_common(50) if c >= min_count and len(p) >= min_len]

    # 评分：重复短语越多，分数越高（每个重复短语加 5 分，上限 100）
    score = min(len(repeated) * 5, 100)

    return {
        "repeated_phrases": [{"phrase": p, "count": c} for p, c in repeated[:20]],
        "repeated_phrase_count": len(repeated),
        "phrase_repetition_score": score,
    }
