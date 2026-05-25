"""novel_tools CLI — 统一命令行入口."""

import argparse
import json
import sys


def cmd_stats(args):
    from novel_tools.stats import wordcount, pacing, rhythm
    if args.stats_cmd == "count":
        if hasattr(args, 'path'):
            result = wordcount.count_chapter(args.path)
        else:
            result = wordcount.count_book(args.dir)
    elif args.stats_cmd == "pacing":
        result = pacing.analyze_pacing(args.path)
    elif args.stats_cmd == "rhythm":
        result = rhythm.extract_emotion_curve(args.path)
    else:
        result = {"error": f"Unknown stats command: {args.stats_cmd}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_slop(args):
    from novel_tools.slop import analyzer, dictionary, scanner
    if args.slop_cmd == "scan":
        with open(args.path, encoding="utf-8") as f:
            text = f.read()
        metrics = analyzer.analyze_text(text)
        score = analyzer.score_ai_risk(metrics)
        result = {"metrics": metrics, "risk": score}
    elif args.slop_cmd == "dict":
        slop_dict = dictionary.load_dictionary()
        if args.ban:
            words = slop_dict.by_severity("ban")
        elif args.warn:
            words = slop_dict.by_severity("warn")
        elif args.limit:
            words = slop_dict.by_severity("limit")
        elif args.cat:
            words = slop_dict.by_category(args.cat)
        else:
            words = slop_dict.words
        result = {"total": len(words), "words": [{"word": w.word, "category": w.category, "severity": w.severity} for w in words]}
    else:
        result = {"error": f"Unknown slop command: {args.slop_cmd}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_bible(args):
    from novel_tools.bible import character, foreshadow, world
    project_dir = getattr(args, 'project_dir', '.') or '.'
    if args.bible_cmd == "char":
        if args.char_action == "list":
            result = character.list_all(project_dir)
        elif args.char_action == "add":
            result = {"id": character.register(project_dir, args.name, args.role or "supporting")}
        elif args.char_action == "track":
            character.track_appearance(project_dir, args.id, args.ch)
            result = {"ok": True}
        else:
            result = {"error": f"Unknown char action: {args.char_action}"}
    elif args.bible_cmd == "foreshadow":
        if args.fs_action == "list":
            result = foreshadow.list_unresolved(project_dir)
        elif args.fs_action == "plant":
            result = {"id": foreshadow.plant(project_dir, args.desc, args.ch)}
        elif args.fs_action == "resolve":
            foreshadow.resolve(project_dir, args.id, args.ch)
            result = {"ok": True}
        elif args.fs_action == "warn":
            threshold = getattr(args, 'threshold', 5) or 5
            result = foreshadow.warn_expiring(project_dir, threshold)
        else:
            result = {"error": f"Unknown foreshadow action: {args.fs_action}"}
    elif args.bible_cmd == "world":
        if args.world_action == "list":
            result = world.list_rules(project_dir, args.category)
        elif args.world_action == "add":
            result = {"id": world.register_rule(
                project_dir, args.category or "general", args.key, args.content,
                is_hard_rule=args.hard, chapter=args.ch
            )}
        else:
            result = {"error": f"Unknown world action: {args.world_action}"}
    else:
        result = {"error": f"Unknown bible command: {args.bible_cmd}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_consistency(args):
    from novel_tools.consistency import names, timeline, structure
    if args.consistency_cmd == "check":
        project_dir = getattr(args, 'project_dir', '.') or '.'
        result = {
            "names": names.scan_all(project_dir),
            "timeline": timeline.check_timeline(project_dir),
            "structure": structure.check_coverage(project_dir),
        }
    elif args.consistency_cmd == "names":
        with open(args.path, encoding="utf-8") as f:
            text = f.read()
        result = names.scan_name_variants(text, [])
    elif args.consistency_cmd == "timeline":
        result = timeline.check_timeline(args.project_dir or '.')
    else:
        result = {"error": f"Unknown consistency command: {args.consistency_cmd}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_outline(args):
    from novel_tools.outline import parser, diff
    if args.outline_cmd == "parse":
        result = parser.parse_outline_md(args.path)
    elif args.outline_cmd == "diff":
        result = diff.check_chapter_vs_outline(args.chapter, args.outline)
    else:
        result = {"error": f"Unknown outline command: {args.outline_cmd}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(prog="novel-tools", description="novel_any Python 工具箱")
    sub = parser.add_subparsers(dest="command", help="模块")

    # stats
    p_stats = sub.add_parser("stats", help="文本统计")
    stats_sub = p_stats.add_subparsers(dest="stats_cmd")
    p_stats_count = stats_sub.add_parser("count", help="字数统计")
    p_stats_count.add_argument("path", nargs="?", help="章节文件路径（单章统计）")
    p_stats_count.add_argument("--dir", help="项目目录（全书统计）")
    p_stats_pacing = stats_sub.add_parser("pacing", help="节奏分析")
    p_stats_pacing.add_argument("path", help="章节文件路径")
    p_stats_rhythm = stats_sub.add_parser("rhythm", help="情绪曲线")
    p_stats_rhythm.add_argument("path", help="章节文件路径")

    # slop
    p_slop = sub.add_parser("slop", help="降AI率引擎")
    slop_sub = p_slop.add_subparsers(dest="slop_cmd")
    p_slop_scan = slop_sub.add_parser("scan", help="全维度AI检测")
    p_slop_scan.add_argument("path", help="章节文件路径")
    p_slop_dict = slop_sub.add_parser("dict", help="黑名单查看")
    p_slop_dict.add_argument("--ban", action="store_true")
    p_slop_dict.add_argument("--warn", action="store_true")
    p_slop_dict.add_argument("--limit", action="store_true")
    p_slop_dict.add_argument("--cat", help="分类过滤 (connector/filler/cliche/emotion/action/narration/dialogue)")

    # bible
    p_bible = sub.add_parser("bible", help="Story Bible")
    bible_sub = p_bible.add_subparsers(dest="bible_cmd")

    p_char = bible_sub.add_parser("char", help="角色管理")
    char_sub = p_char.add_subparsers(dest="char_action")
    p_char_list = char_sub.add_parser("list")
    p_char_list.add_argument("--project-dir", default=".")
    p_char_add = char_sub.add_parser("add")
    p_char_add.add_argument("name")
    p_char_add.add_argument("--role", default="supporting")
    p_char_add.add_argument("--project-dir", default=".")
    p_char_track = char_sub.add_parser("track")
    p_char_track.add_argument("id")
    p_char_track.add_argument("--ch", type=int, required=True)
    p_char_track.add_argument("--project-dir", default=".")

    p_fs = bible_sub.add_parser("foreshadow", help="伏笔管理")
    fs_sub = p_fs.add_subparsers(dest="fs_action")
    p_fs_list = fs_sub.add_parser("list")
    p_fs_list.add_argument("--project-dir", default=".")
    p_fs_plant = fs_sub.add_parser("plant")
    p_fs_plant.add_argument("desc")
    p_fs_plant.add_argument("--ch", type=int, required=True)
    p_fs_plant.add_argument("--project-dir", default=".")
    p_fs_resolve = fs_sub.add_parser("resolve")
    p_fs_resolve.add_argument("id")
    p_fs_resolve.add_argument("--ch", type=int, required=True)
    p_fs_resolve.add_argument("--project-dir", default=".")
    p_fs_warn = fs_sub.add_parser("warn")
    p_fs_warn.add_argument("--threshold", type=int, default=5)
    p_fs_warn.add_argument("--project-dir", default=".")

    p_world = bible_sub.add_parser("world", help="世界观管理")
    world_sub = p_world.add_subparsers(dest="world_action")
    p_world_list = world_sub.add_parser("list")
    p_world_list.add_argument("--project-dir", default=".")
    p_world_list.add_argument("--category")
    p_world_add = world_sub.add_parser("add")
    p_world_add.add_argument("key")
    p_world_add.add_argument("content")
    p_world_add.add_argument("--category", default="general")
    p_world_add.add_argument("--hard", action="store_true")
    p_world_add.add_argument("--ch", type=int)
    p_world_add.add_argument("--project-dir", default=".")

    # consistency
    p_cons = sub.add_parser("consistency", help="一致性检查")
    cons_sub = p_cons.add_subparsers(dest="consistency_cmd")
    p_cons_check = cons_sub.add_parser("check", help="运行所有检查")
    p_cons_check.add_argument("--project-dir", default=".")
    p_cons_names = cons_sub.add_parser("names", help="称谓扫描")
    p_cons_names.add_argument("path")
    p_cons_timeline = cons_sub.add_parser("timeline", help="时间线检查")
    p_cons_timeline.add_argument("--project-dir", default=".")

    # outline
    p_outline = sub.add_parser("outline", help="大纲管理")
    outline_sub = p_outline.add_subparsers(dest="outline_cmd")
    p_out_parse = outline_sub.add_parser("parse", help="解析章纲")
    p_out_parse.add_argument("path")
    p_out_diff = outline_sub.add_parser("diff", help="正文vs章纲差异")
    p_out_diff.add_argument("chapter")
    p_out_diff.add_argument("outline")

    args = parser.parse_args()

    if args.command == "stats":
        cmd_stats(args)
    elif args.command == "slop":
        cmd_slop(args)
    elif args.command == "bible":
        cmd_bible(args)
    elif args.command == "consistency":
        cmd_consistency(args)
    elif args.command == "outline":
        cmd_outline(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
