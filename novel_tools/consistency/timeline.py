"""时间线一致性检查 — 时间标记提取 + 跨章冲突检测."""

import re
from pathlib import Path
from novel_tools.config import find_chapter_files


# 中文时间标记正则
TIME_PATTERNS = [
    (r"(\d+)天后", "days_later"),
    (r"(\d+)年前", "years_ago"),
    (r"(\d+)月后", "months_later"),
    (r"(\d+)个?时辰后", "hours_later"),
    (r"第(\d+)天", "day_n"),
    (r"第(\d+)日", "day_n"),
    (r"次日", "next_day"),
    (r"翌日", "next_day"),
    (r"当天", "same_day"),
    (r"当日", "same_day"),
    (r"一炷香后", "moment_later"),
    (r"一盏茶后", "moment_later"),
    (r"半日后", "half_day"),
    (r"三日后", "three_days"),
    (r"七日后", "seven_days"),
    (r"一个月后", "month_later"),
    (r"一年后", "year_later"),
    (r"转眼间", "time_skip"),
    (r"光阴似箭", "time_skip_long"),
    (r"日月如梭", "time_skip_long"),
    (r"春去秋来", "season_change"),
    (r"(\d+)更时分", "night_watch"),
    (r"(\d+)时", "hour"),
    (r"清晨", "early_morning"),
    (r"傍晚", "evening"),
    (r"深夜", "late_night"),
    (r"午夜", "midnight"),
    (r"正午", "noon"),
    (r"黄昏", "dusk"),
    (r"黎明", "dawn"),
]


def parse_timestamps(text: str) -> list[dict]:
    """从文本中提取所有时间标记."""
    timestamps = []
    for pattern, tag in TIME_PATTERNS:
        for m in re.finditer(pattern, text):
            timestamps.append({
                "text": m.group(0),
                "tag": tag,
                "position": m.start(),
                "value": int(m.group(1)) if m.groups() else None,
            })
    # 按位置排序
    timestamps.sort(key=lambda x: x["position"])
    return timestamps


def check_chapter_timeline(filepath: str) -> dict:
    """检查单章内部的时间线是否可疑."""
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    with open(path, encoding="utf-8") as f:
        text = f.read()

    timestamps = parse_timestamps(text)
    issues = []

    # 检查「几天后」→「当天」这种倒序
    prev_tag = None
    for ts in timestamps:
        tag = ts["tag"]
        # 如果前面是时间跳跃，后面出现"当天"/"次日"可能是矛盾的
        if prev_tag in ("days_later", "months_later", "years_later") and tag in ("same_day",):
            issues.append({
                "type": "timeline_jump_back",
                "prev": prev_tag,
                "current": tag,
                "text": ts["text"],
                "detail": f"前面有长时间跳跃，但后面出现'{ts['text']}'，时间线可能断裂",
            })
        prev_tag = tag

    return {
        "file": str(path),
        "timestamps_found": len(timestamps),
        "timestamps": [{"text": t["text"], "tag": t["tag"]} for t in timestamps],
        "issues": issues,
    }


def check_timeline(project_dir: str) -> dict:
    """检查所有章节的时间线."""
    chapter_files = find_chapter_files(project_dir)
    if not chapter_files:
        return {"error": "No chapter files found", "results": []}

    results = []
    for f in chapter_files:
        results.append(check_chapter_timeline(f))

    total_issues = sum(len(r.get("issues", [])) for r in results)
    # Cross-chapter timeline detection
    cross_issues = []
    prev_tags = []
    for r in results:
        tags = [t["tag"] for t in r.get("timestamps", [])]
        if prev_tags and tags:
            if any(t in ("days_later", "months_later", "years_later", "time_skip_long")
                   for t in prev_tags[-3:])                and any(t in ("same_day", "next_day", "early_morning")
                       for t in tags[:3]):
                cross_issues.append({
                    "type": "cross_chapter_anomaly",
                    "file": r["file"],
                    "detail": "前章有长时间跳跃，但本章开头时间标记较早，可能矛盾"
                })
        prev_tags = tags

    return {
        "total_chapters": len(results),
        "total_issues": total_issues,
        "cross_chapter_issues": cross_issues,
        "results": results,
    }
