"""Pipeline 主入口 — 串联 6 阶段，支持单阶段运行."""

import argparse
import json
import uuid
from datetime import datetime, timezone

from novel_tools.pipeline.db import list_active_books


def run_fetch(args):
    """阶段 1: 抓取."""
    from novel_tools.pipeline.scraper import discover_and_fetch
    limit = getattr(args, 'limit', 3)
    max_chapters = getattr(args, 'max_chapters', 50)
    ids = discover_and_fetch(limit=limit, max_chapters=max_chapters)
    print(json.dumps(
        {"stage": "fetch", "books_added": len(ids), "book_ids": ids},
        ensure_ascii=False,
    ))


def run_analyze(args):
    """阶段 2: 分析."""
    from novel_tools.pipeline.analyzer import analyze_book
    if getattr(args, 'book_id', None):
        bids = [args.book_id]
    else:
        books = list_active_books()
        bids = [b["id"] for b in books]

    results = {}
    for bid in bids:
        run_id = analyze_book(bid)
        results[str(bid)] = run_id

    print(json.dumps(
        {"stage": "analyze", "results": results},
        ensure_ascii=False,
    ))


def run_validate(args):
    """阶段 3: 验证."""
    from novel_tools.pipeline.validator import validate_book
    run_id = uuid.uuid4().hex[:12]

    if getattr(args, 'book_id', None):
        bids = [args.book_id]
    else:
        books = list_active_books()
        bids = [b["id"] for b in books]

    all_stats = {}
    for bid in bids:
        stats = validate_book(bid, run_id, use_llm=False)
        all_stats[str(bid)] = stats

    print(json.dumps(
        {"stage": "validate", "run_id": run_id, "results": all_stats},
        ensure_ascii=False, indent=2,
    ))


def run_research(args):
    """阶段 4: 调研 — 输出待委派的 prompts."""
    from novel_tools.pipeline.researcher import research_gaps
    pending = research_gaps()
    print(json.dumps(
        {"stage": "research", "pending_gaps": len(pending), "gaps": pending},
        ensure_ascii=False, indent=2,
    ))
    if pending:
        print("\n⚠ 调研需要通过 delegate_task 委派给 subagent 执行。")


def run_review(args):
    """阶段 6: 审查."""
    from novel_tools.pipeline.reviewer import check_imports
    result = check_imports()
    print(json.dumps(
        {"stage": "review", "result": result},
        ensure_ascii=False, indent=2,
    ))


def run_all(args):
    """运行全流程."""
    print(f"=== Pipeline 全流程 === {datetime.now(timezone.utc).isoformat()}")
    run_fetch(args)
    run_analyze(args)
    run_validate(args)
    run_research(args)
    run_review(args)


def main():
    parser = argparse.ArgumentParser(
        prog="pipeline", description="novel_auto_pipeline"
    )
    sub = parser.add_subparsers(dest="phase")

    p_all = sub.add_parser("run", help="运行全流程")
    p_all.add_argument("--limit", type=int, default=3, help="抓取书数")
    p_all.add_argument("--max-chapters", type=int, default=50, help="每书最多章数")
    p_all.add_argument("--dry-run", action="store_true", help="预览模式")

    p_fetch = sub.add_parser("fetch", help="阶段 1: 抓取")
    p_fetch.add_argument("--limit", type=int, default=3)
    p_fetch.add_argument("--max-chapters", type=int, default=50)

    p_analyze = sub.add_parser("analyze", help="阶段 2: 分析")
    p_analyze.add_argument("--book-id", type=int, help="指定书籍 ID")

    p_validate = sub.add_parser("validate", help="阶段 3: 验证")
    p_validate.add_argument("--book-id", type=int)

    p_research = sub.add_parser("research", help="阶段 4: 调研")

    p_review = sub.add_parser("review", help="阶段 6: 审查")

    args = parser.parse_args()

    if args.phase == "run":
        run_all(args)
    elif args.phase == "fetch":
        run_fetch(args)
    elif args.phase == "analyze":
        run_analyze(args)
    elif args.phase == "validate":
        run_validate(args)
    elif args.phase == "research":
        run_research(args)
    elif args.phase == "review":
        run_review(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
