"""章纲解析器 — 将 Markdown 章纲解析为结构化数据."""

import re
from pathlib import Path


def parse_outline_md(filepath: str) -> dict:
    """解析单个章纲 Markdown 文件.

    支持 novel_any 的章纲格式：
    - YAML frontmatter（可选）
    - 标题行
    - 叙事目标 / 情绪基调 / 检查点 / 涉及角色

    Returns:
        dict with title, level, narrative_goal, emotion_target, checkpoints, characters
    """
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    with open(path, encoding="utf-8") as f:
        content = f.read()

    result = {
        "file": str(path),
        "title": path.stem,
        "level": "chapter",
        "narrative_goal": "",
        "emotion_target": "",
        "checkpoints": [],
        "characters_involved": [],
        "raw_sections": {},
    }

    # 解析 frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    body = content
    if fm_match:
        fm = fm_match.group(1)
        body = content[fm_match.end():]
        for line in fm.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                key, val = key.strip().lower(), val.strip().strip('"\'')
                if key == 'level':
                    result['level'] = val

    # 解析标题
    title_match = re.search(r'^#\s+(.*)', body, re.MULTILINE)
    if title_match:
        result['title'] = title_match.group(1).strip()

    # 按 ## 分段
    sections = re.split(r'\n(?=## )', body)
    for section in sections:
        header_match = re.match(r'##\s+(.*)', section)
        if not header_match:
            continue
        header = header_match.group(1).strip()
        section_body = section[header_match.end():].strip()
        result['raw_sections'][header] = section_body

        # 叙事目标
        if '叙事' in header or '目标' in header or 'narrative' in header.lower():
            result['narrative_goal'] = section_body[:200].strip()

        # 情绪基调
        elif '情绪' in header or '基调' in header or 'emotion' in header.lower():
            result['emotion_target'] = section_body[:100].strip()

        # 检查点
        elif '检查' in header or 'checkpoint' in header.lower() or '点' in header:
            points = []
            for line in section_body.split('\n'):
                line = line.strip()
                if re.match(r'^[-*]', line):
                    points.append(re.sub(r'^[-*]\s+', '', line).strip())
                elif re.match(r'^\d+[.、）)]', line):
                    points.append(re.sub(r'^\d+[.、）)]\s*', '', line).strip())
            result['checkpoints'] = points

        # 涉及角色
        elif '角色' in header or '人物' in header or 'character' in header.lower():
            chars = []
            for line in section_body.split('\n'):
                line = line.strip()
                name_match = re.match(r'^[-*]\s*(.+)', line)
                if name_match:
                    name = name_match.group(1).strip()
                    # 提取角色名（去除额外描述）
                    name_clean = re.split(r'[（(：:—]', name)[0].strip()
                    if name_clean:
                        chars.append(name_clean)
            result['characters_involved'] = chars

    return result


def parse_all_outlines(project_dir: str) -> list[dict]:
    """解析项目中的所有章纲文件."""
    outline_dir = Path(project_dir) / "大纲"
    if not outline_dir.exists():
        outline_dir = Path(project_dir) / "outline"
    if not outline_dir.exists():
        return [{"error": "No outline directory found"}]

    outlines = []
    for f in sorted(outline_dir.glob("*.md")):
        if f.name == "故事大纲.md":
            continue
        result = parse_outline_md(str(f))
        outlines.append(result)

    return outlines
