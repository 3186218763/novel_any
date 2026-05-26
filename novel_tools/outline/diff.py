"""正文 vs 章纲差异检查."""

import re
from pathlib import Path


def check_chapter_vs_outline(chapter_path: str, outline_path: str) -> dict:
    """检查章节正文与章纲的覆盖差异.

    Args:
        chapter_path: 正文章节文件路径
        outline_path: 章纲文件路径

    Returns:
        dict with events_covered, events_missed, extra_events, match_percentage
    """
    ch_path = Path(chapter_path)
    ol_path = Path(outline_path)

    if not ch_path.exists():
        return {"error": f"Chapter not found: {chapter_path}"}
    if not ol_path.exists():
        return {"error": f"Outline not found: {outline_path}"}

    with open(ch_path, encoding="utf-8") as f:
        chapter_text = f.read()
    with open(ol_path, encoding="utf-8") as f:
        outline_text = f.read()

    # 从章纲中提取事件/检查点
    from novel_tools.outline.parser import parse_outline_md
    outline_data = parse_outline_md(outline_path)

    # 优先使用 parse 出的检查点
    checkpoints = outline_data.get("checkpoints", [])
    # 如果没有显式的检查点，从原始内容中提取所有列表项
    if not checkpoints:
        for line in outline_text.split('\n'):
            line = line.strip()
            if re.match(r'^[-*]', line):
                point = re.sub(r'^[-*]\s+', '', line).strip()
                if point and len(point) > 3:
                    checkpoints.append(point)

    if not checkpoints:
        return {"error": "No checkpoints found in outline", "match_percentage": 0}

    # 检查每个检查点
    covered = []
    missed = []
    for point in checkpoints:
        # 提取关键词（2-5 字）
        keywords = re.findall(r'[\u4e00-\u9fff]{2,5}', point)
        if not keywords:
            continue
        # 至少 40% 的关键词在正文出现
        hits = sum(1 for kw in keywords if kw in chapter_text)
        if hits >= max(1, len(keywords) * 0.4):
            covered.append(point[:60])
        else:
            missed.append({
                "point": point[:80],
                "keywords_matched": hits,
                "keywords_total": len(keywords),
            })

    # 正文中的额外事件（章纲未计划的）
    # 检查正文是否有大量与章纲关键词无关的段落
    outline_keywords = set()
    for cp in checkpoints:
        for kw in re.findall(r'[\u4e00-\u9fff]{2,5}', cp):
            outline_keywords.add(kw)

    # 提取正文段落首句，检查是否有关键词不匹配的
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', chapter_text) if p.strip() and len(p.strip()) > 20]
    extra_events = []
    for p in paragraphs:
        para_kw = set(re.findall(r'[\u4e00-\u9fff]{2,5}', p[:100]))
        overlap = para_kw & outline_keywords
        if not overlap and len(p) > 50:
            first_sent = re.split(r'[。！？]', p)[0].strip()[:50]
            if first_sent:
                extra_events.append(first_sent)

    total = len(checkpoints)
    match_pct = round(len(covered) / total * 100, 1) if total > 0 else 0

    return {
        "chapter_file": str(ch_path),
        "outline_file": str(ol_path),
        "total_checkpoints": total,
        "events_covered": covered,
        "covered_count": len(covered),
        "events_missed": missed,
        "missed_count": len(missed),
        "extra_events": extra_events[:10],  # 最多 10 个
        "match_percentage": match_pct,
    }


def summarize_vs_outline(chapter_path: str, outline_path: str) -> dict:
    """用 TextRank 摘要对比章纲覆盖度."""
    from pathlib import Path
    from novel_tools.outline.parser import parse_outline_md

    ch_path = Path(chapter_path)
    ol_path = Path(outline_path)
    if not ch_path.exists():
        return {"error": f"Chapter not found: {chapter_path}"}
    if not ol_path.exists():
        return {"error": f"Outline not found: {outline_path}"}

    with open(ch_path, encoding="utf-8") as f:
        chapter_text = f.read()

    outline_data = parse_outline_md(outline_path)
    checkpoints = outline_data.get("checkpoints", [])

    summary = _textrank_summary(chapter_text, topn=5)

    covered = []
    missing = []
    for cp in checkpoints:
        best_score = max((_bm25_similarity(cp, s) for s in summary), default=0)
        if best_score > 0.15:
            covered.append({"checkpoint": cp, "score": round(best_score, 3)})
        else:
            missing.append({"checkpoint": cp, "score": round(best_score, 3)})

    coverage_pct = round(len(covered) / len(checkpoints) * 100, 1) if checkpoints else 0

    return {
        "chapter_file": str(ch_path),
        "outline_file": str(ol_path),
        "summary": summary,
        "covered": covered,
        "missing": missing,
        "coverage_pct": coverage_pct,
    }


def _textrank_summary(text: str, topn: int = 5) -> list[str]:
    """TextRank 摘要提取."""
    try:
        from snownlp import SnowNLP
        s = SnowNLP(text)
        return s.summary(topn)
    except ImportError:
        sentences = [s.strip() for s in re.split(r'[。！？]', text) if len(s.strip()) > 10]
        return sentences[:topn]


def _bm25_similarity(s1: str, s2: str, k1: float = 1.5, b: float = 0.75) -> float:
    """简化 BM25 相似度."""
    words1 = set(re.findall(r'[\u4e00-\u9fff]{2,}', s1))
    words2 = set(re.findall(r'[\u4e00-\u9fff]{2,}', s2))
    if not words1 or not words2:
        return 0.0
    overlap = words1 & words2
    return len(overlap) / max(len(words1), len(words2))
