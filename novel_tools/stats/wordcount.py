"""字数统计 — 中文字数、总字符数、词数、段落数、对话行数."""

import re
import random
from pathlib import Path


# 汉字笔画映射（常用 ~500 字作为内联 fallback）
_STROKE_MAP: dict[str, int] | None = None


def _load_stroke_map() -> dict[str, int]:
    global _STROKE_MAP
    if _STROKE_MAP is not None:
        return _STROKE_MAP
    stroke_path = Path(__file__).parent.parent / "data" / "hanzi_strokes.json"
    if stroke_path.exists():
        import json
        with open(stroke_path, encoding="utf-8") as f:
            _STROKE_MAP = json.load(f)
    else:
        _STROKE_MAP = {}  # fallback: 未知字默认10画
    return _STROKE_MAP


def count_chapter(filepath: str) -> dict:
    """统计单个章节文件.

    Returns:
        dict with: chinese_chars, total_chars, words, paragraphs, dialogue_lines, file_path
    """
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (UnicodeDecodeError, PermissionError, IOError) as e:
        return {"error": str(e)}

    # 中文字数
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text))

    # 总字符数（含标点、英文、数字、空格）
    total_chars = len(text.replace('\n', '').replace('\r', ''))

    # 段落数（以空行分隔）
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip() and len(p.strip()) > 5]
    paragraph_count = len(paragraphs)

    # 对话行数（中文引号「」或英文引号 "" 包裹的内容）
    dialogue_matches = re.findall(r'(「[^」]+」)|(“[^”]+”)|("[^"]+")', text)
    dialogue_lines = len(dialogue_matches)

    # 分词统计（可选，依赖 jieba）
    word_count = 0
    try:
        import jieba
        words = list(jieba.cut(text))
        word_count = len([w for w in words if w.strip() and re.search(r'[\u4e00-\u9fff]', w)])
    except ImportError:
        word_count = chinese_chars  # 降级：用中文字数代替

    # 标题提取
    title_match = re.search(r'^#\s+(.+)', text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem

    # === 词汇多样性 (MATTR + HD-D) ===
    words_raw = re.findall(r'[\u4e00-\u9fff]+', text)
    window_size = 50
    ttrs = []
    for i in range(0, len(words_raw) - window_size + 1,
                   max(1, (max(len(words_raw) - window_size, 1)) // 30)):
        window = words_raw[i:i + window_size]
        if len(set(window)) > 0:
            ttrs.append(len(set(window)) / len(window))
    mattr = round(sum(ttrs) / len(ttrs), 3) if ttrs else 0.0

    sample_ttrs = []
    for _ in range(min(42, max(len(words_raw) // 10, 1))):
        size = random.randint(35, 50)
        if len(words_raw) >= size:
            start = random.randint(0, len(words_raw) - size)
            sample = words_raw[start:start + size]
            if len(set(sample)) > 0:
                sample_ttrs.append(len(set(sample)) / len(sample))
    hd_d = round(sum(sample_ttrs) / len(sample_ttrs) * 0.9, 3) if sample_ttrs else 0.0

    # === 中文可读性 ===
    sentences_raw = [s.strip() for s in re.split(r'[。！？…]+', text)
                     if s.strip() and len(s.strip()) > 2]
    sent_count = len(sentences_raw) or 1
    avg_sent_len = chinese_chars / sent_count
    long_sents = sum(1 for s in sentences_raw
                     if len(re.findall(r'[\u4e00-\u9fff]', s)) > 40)
    long_ratio = round(long_sents / sent_count, 3)

    stroke_cache = _load_stroke_map()
    stroke_sum = 0
    for ch in re.findall(r'[\u4e00-\u9fff]', text):
        stroke_sum += stroke_cache.get(ch, 10)
    avg_strokes = stroke_sum / chinese_chars if chinese_chars > 0 else 10
    flesch_zh = round(206.835 - 1.015 * avg_sent_len - 0.846 * avg_strokes, 1)

    readability = {
        "flesch_zh": flesch_zh,
        "avg_sentence_len": round(avg_sent_len, 1),
        "long_sentence_ratio": long_ratio,
    }
    lexical_diversity = {"mattr": mattr, "hd_d": hd_d}

    return {
        "file_path": str(path),
        "title": title,
        "chinese_chars": chinese_chars,
        "total_chars": total_chars,
        "words": word_count,
        "paragraphs": paragraph_count,
        "dialogue_lines": dialogue_lines,
        "readability": readability,
        "lexical_diversity": lexical_diversity,
    }


def count_book(project_dir: str) -> dict:
    """统计全书的章节字数.

    Returns:
        dict with: total_chinese_chars, chapter_count, chapters, avg_chapter_len, completed
    """
    from novel_tools.config import find_chapter_files

    chapter_files = find_chapter_files(project_dir)
    if not chapter_files:
        return {"error": "No chapter files found", "total_chinese_chars": 0, "chapter_count": 0, "chapters": []}

    chapters = []
    total = 0

    for f in chapter_files:
        stats = count_chapter(f)
        if "error" not in stats:
            chapters.append({
                "file": stats["file_path"],
                "title": stats["title"],
                "chars": stats["chinese_chars"],
            })
            total += stats["chinese_chars"]

    # 检查是否有完结标记
    completed = False
    if chapters:
        try:
            with open(chapter_files[-1], encoding="utf-8") as f:
                last_text = f.read()
            completed = bool(re.search(r'(完|终|全文完|全书完|END)', last_text[-500:]))
        except Exception:
            pass

    return {
        "total_chinese_chars": total,
        "chapter_count": len(chapters),
        "chapters": chapters,
        "avg_chapter_len": total // len(chapters) if chapters else 0,
        "completed": completed,
    }


def readout_book(project_dir: str) -> dict:
    """全书的每章可读性指标序列."""
    from novel_tools.config import find_chapter_files
    chapter_files = find_chapter_files(project_dir)
    chapters = []
    flesch_vals = []
    for f in chapter_files:
        stats = count_chapter(f)
        if "error" in stats:
            continue
        r = stats.get("readability", {})
        chapters.append({
            "file": f,
            "flesch_zh": r.get("flesch_zh", 0),
            "mattr": stats.get("lexical_diversity", {}).get("mattr", 0),
            "hd_d": stats.get("lexical_diversity", {}).get("hd_d", 0),
            "chars": stats.get("chinese_chars", 0),
        })
        flesch_vals.append(r.get("flesch_zh", 0))
    avg_flesch = round(sum(flesch_vals) / len(flesch_vals), 1) if flesch_vals else 0
    trend = "stable"
    if len(flesch_vals) >= 3:
        n = len(flesch_vals)
        x_mean = (n - 1) / 2
        y_mean = avg_flesch
        numerator = sum((i - x_mean) * (flesch_vals[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator > 0 else 0
        if slope > 0.3:
            trend = "easier"
        elif slope < -0.3:
            trend = "harder"
    return {"chapters": chapters, "avg_flesch_zh": avg_flesch, "trend": trend}
