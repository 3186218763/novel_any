"""pipeline.analyzer — 对所有章节运行各分析模块，结果写入 DB."""

from __future__ import annotations

import uuid
from pathlib import Path

from novel_tools import __version__ as TOOL_VERSION
from novel_tools.pipeline.db import get_chapters, save_analysis, touch_book, get_analyses_for_chapter

from novel_tools.stats import wordcount
from novel_tools.stats import pacing as pacing_mod
from novel_tools.slop import scanner
from novel_tools.slop import analyzer as slop_analyzer
from novel_tools.consistency import emotion
from novel_tools.style_lint import rules

# ── 常量 ──────────────────────────────────────────────

MODULES: list[str] = [
    "stats",
    "pacing",
    "slop",
    "ai_score",
    "emotion",
    "style_lint",
]


# ── helpers ───────────────────────────────────────────

def _read_file(path: str) -> str:
    """读取文本文件内容."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def _run_module(module_name: str, file_path: str) -> dict:
    """运行单个分析模块，返回 metrics dict.

    Args:
        module_name: MODULES 中的键.
        file_path: 章节文件路径.

    Returns:
        dict: 模块输出的 metrics，或 {'error': str} 表示失败.
    """
    try:
        if module_name == "stats":
            return wordcount.count_chapter(file_path)

        elif module_name == "pacing":
            return pacing_mod.analyze_pacing(file_path)

        elif module_name == "slop":
            text = _read_file(file_path)
            return scanner.scan_chinese_weasel(text)

        elif module_name == "ai_score":
            text = _read_file(file_path)
            metrics = slop_analyzer.analyze_text(text)
            risk = slop_analyzer.score_ai_risk(metrics)
            return {**metrics, **risk}

        elif module_name == "emotion":
            return emotion.extract_emotion_curve(file_path)

        elif module_name == "style_lint":
            text = _read_file(file_path)
            result = rules.lint(text)
            # 短文本追加 quick_scan 结果
            if len(text) < 2000:
                qs = rules.quick_scan(text)
                result["issues"].extend(qs["issues"])
                result["summary"] = qs["summary"]  # quick_scan 汇总覆盖
            return result

        else:
            return {"error": f"Unknown module: {module_name}"}

    except Exception as e:
        return {"error": str(e)}


# ── 主入口 ────────────────────────────────────────────

def analyze_book(book_id: int) -> str:
    """对一本书的所有章节运行全部分析模块，结果写入 DB.

    Args:
        book_id: books 表主键.

    Returns:
        run_id: 本次运行的唯一 ID.
    """
    run_id = uuid.uuid4().hex[:12]
    chapters = get_chapters(book_id)

    for chapter in chapters:
        chapter_id = chapter["id"]
        file_path = chapter.get("file_path", "")

        if not file_path or not Path(file_path).exists():
            # 路径缺失或文件不存在 — 为每个模块记录错误
            for module_name in MODULES:
                save_analysis(
                    run_id=run_id,
                    book_id=book_id,
                    chapter_id=chapter_id,
                    module=module_name,
                    metrics={"error": f"File not found or missing: {file_path!r}"},
                    tool_version=TOOL_VERSION,
                )
            continue

        for module_name in MODULES:
            metrics = _run_module(module_name, file_path)
            save_analysis(
                run_id=run_id,
                book_id=book_id,
                chapter_id=chapter_id,
                module=module_name,
                metrics=metrics,
                tool_version=TOOL_VERSION,
            )

    # ── 跨章模板检测 ──────────────────────────────────
    if len(chapters) >= 2:
        from novel_tools.slop.cross_chapter import detect_template_patterns
        chapter_texts = [_read_file(ch["file_path"]) for ch in chapters]
        template_result = detect_template_patterns(chapter_texts)
        save_analysis(run_id, book_id, 0, "cross_chapter", template_result, TOOL_VERSION)

    # ── 全书 style_lint 汇总 ──────────────────────────
    from collections import Counter
    import json as _json
    all_issues = []
    for ch in chapters:
        for a in get_analyses_for_chapter(ch["id"]):
            if a["module"] == "style_lint":
                m = _json.loads(a["metrics"]) if isinstance(a["metrics"], str) else a["metrics"]
                all_issues.extend(m.get("issues", []))
    if all_issues:
        save_analysis(run_id, book_id, 0, "style_lint_book", {
            "total_issues": len(all_issues),
            "issues_by_severity": dict(Counter(i.get("severity", "info") for i in all_issues)),
            "unique_checks": len(set(i.get("check", "") for i in all_issues)),
        }, TOOL_VERSION)

    touch_book(book_id)
    return run_id
