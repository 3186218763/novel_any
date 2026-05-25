"""结构一致性检查 — 章纲覆盖率检查."""

import re
from pathlib import Path
from novel_tools.config import find_chapter_files


def check_outline_coverage(chapter_text: str, outline_text: str) -> dict:
    """检查章节正文是否覆盖了章纲目标.

    通过提取章纲中的关键词，检查在正文中的出现情况。

    Args:
        chapter_text: 正文章节内容
        outline_text: 章纲内容

    Returns:
        dict with coverage_score, covered_points, missing_points
    """
    if not outline_text.strip():
        return {"error": "Empty outline", "coverage_score": 0}

    # 从章纲中提取要点（以 - 或 数字列表开头的行）
    points = []
    for line in outline_text.split('\n'):
        line = line.strip()
        # 列表项
        if re.match(r'^[-*]\s', line):
            points.append(re.sub(r'^[-*]\s+', '', line))
        # 数字列表
        elif re.match(r'^\d+[.、）)]', line):
            points.append(re.sub(r'^\d+[.、）)]\s*', '', line))
        # ## 标题
        elif line.startswith('##'):
            points.append(re.sub(r'^#+\s*', '', line))

    if not points:
        return {"error": "No outline points found", "coverage_score": 0}

    # 为每个要点提取关键词（2-4 字）
    covered = []
    missed = []
    for point in points:
        # 提取中文关键词
        keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', point)
        if not keywords:
            continue
        # 检查至少一半关键词在正文中出现
        hits = sum(1 for kw in keywords if kw in chapter_text)
        if hits >= len(keywords) / 2:
            covered.append(point[:50])
        else:
            missed.append({
                "point": point[:80],
                "matched_keywords": hits,
                "total_keywords": len(keywords),
            })

    total = len(points)
    coverage = round(len(covered) / total, 3) if total > 0 else 0

    return {
        "total_points": total,
        "covered_count": len(covered),
        "missed_count": len(missed),
        "coverage_score": coverage,
        "covered_points": covered,
        "missing_points": missed,
    }


def check_coverage(project_dir: str) -> dict:
    """检查项目所有章节的章纲覆盖率.

    自动匹配 大纲/ 目录下的章纲文件与 正文/ 目录下的章节文件。
    """
    chapter_files = find_chapter_files(project_dir)
    if not chapter_files:
        return {"error": "No chapter files found", "results": []}

    # 查找大纲目录
    outline_dir = Path(project_dir) / "大纲"
    if not outline_dir.exists():
        outline_dir = Path(project_dir) / "outline"
    if not outline_dir.exists():
        return {"error": "No outline directory found", "results": []}

    outline_files = sorted(outline_dir.glob("*.md"))
    if not outline_files:
        return {"error": "No outline files in 大纲/", "results": []}

    # 按文件名匹配（章纲_第N章.md ↔ 第N章_*.md）
    results = []
    for cf in chapter_files:
        cf_name = Path(cf).stem
        # 提取章号
        ch_match = re.search(r'第(\d+)章', cf_name)
        if not ch_match:
            continue
        ch_num = ch_match.group(1)

        # 查找匹配的章纲
        matching_outline = None
        for of in outline_files:
            if re.search(rf'第{ch_num}章(?!\\d)', of.stem) or re.search(rf'章纲_第{ch_num}章(?!\\d)', of.stem):
                matching_outline = of
                break

        if matching_outline:
            try:
                with open(cf, encoding="utf-8") as f:
                    chapter_text = f.read()
                with open(matching_outline, encoding="utf-8") as f:
                    outline_text = f.read()
                coverage = check_outline_coverage(chapter_text, outline_text)
                results.append({
                    "chapter_file": str(cf),
                    "outline_file": str(matching_outline),
                    "coverage": coverage,
                })
            except Exception as e:
                results.append({"chapter_file": str(cf), "error": str(e)})

    return {
        "total_matched": len(results),
        "results": results,
    }
