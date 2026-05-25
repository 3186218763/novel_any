"""字数统计 — 中文字数、总字符数、词数、段落数、对话行数."""

import re
from pathlib import Path


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

    return {
        "file_path": str(path),
        "title": title,
        "chinese_chars": chinese_chars,
        "total_chars": total_chars,
        "words": word_count,
        "paragraphs": paragraph_count,
        "dialogue_lines": dialogue_lines,
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
