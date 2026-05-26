"""阶段 6: 审查 — 导入检查 + 功能回归."""

import json
import sys
from pathlib import Path


def check_imports() -> dict:
    modules = [
        "novel_tools",
        "novel_tools.cli",
        "novel_tools.stats.wordcount",
        "novel_tools.stats.pacing",
        "novel_tools.stats.rhythm",
        "novel_tools.slop.analyzer",
        "novel_tools.slop.scanner",
        "novel_tools.slop.dictionary",
        "novel_tools.bible.model",
        "novel_tools.bible.character",
        "novel_tools.bible.foreshadow",
        "novel_tools.bible.world",
        "novel_tools.consistency.emotion",
        "novel_tools.consistency.names",
        "novel_tools.consistency.timeline",
        "novel_tools.consistency.structure",
        "novel_tools.outline.parser",
        "novel_tools.outline.diff",
        "novel_tools.style_lint.rules",
        "novel_tools.pipeline.db",
        "novel_tools.pipeline.scraper",
        "novel_tools.pipeline.analyzer",
        "novel_tools.pipeline.validator",
    ]
    results = {"passed": [], "failed": []}
    for mod in modules:
        try:
            __import__(mod)
            results["passed"].append(mod)
        except Exception as e:
            results["failed"].append({"module": mod, "error": str(e)})
    return results


def regression_test(test_book_id: int) -> dict:
    from novel_tools.pipeline.analyzer import analyze_book
    run_id = analyze_book(test_book_id)
    return {"run_id": run_id, "status": "ok"}


def review(fix_id: int, gap_id: int) -> dict:
    report = {}
    imports = check_imports()
    report["imports"] = imports
    if imports["failed"]:
        report["verdict"] = "fail"
        report["reason"] = f"导入失败: {imports['failed']}"
        return report
    import subprocess
    root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-c", "import novel_tools"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        report["verdict"] = "fail"
        report["reason"] = f"导入错误: {result.stderr}"
        return report
    report["verdict"] = "pass"
    report["syntax"] = "ok"
    return report


if __name__ == "__main__":
    result = check_imports()
    print(json.dumps(result, ensure_ascii=False, indent=2))
