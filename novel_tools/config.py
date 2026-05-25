"""项目配置加载器 — 从 context-brief.md 解析项目信息."""

import re
from pathlib import Path


def load_project(project_dir: str = ".") -> dict:
    """读取项目目录的 context-brief.md，返回标准化配置 dict."""
    brief_path = Path(project_dir) / "context-brief.md"
    if not brief_path.exists():
        # 向上递归查找
        for parent in Path(project_dir).resolve().parents:
            candidate = parent / "context-brief.md"
            if candidate.exists():
                brief_path = candidate
                break
        else:
            return {"error": "context-brief.md not found", "title": Path(project_dir).resolve().name}

    with open(brief_path, encoding="utf-8") as f:
        content = f.read()

    result = {
        "title": "",
        "type": "",
        "platform": "",
        "progress": "",
        "total_chars": 0,
        "chapter_count": 0,
        "last_write_date": "",
        "pending_issues": 0,
    }

    # 提取 YAML frontmatter（如果有）
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if frontmatter_match:
        fm = frontmatter_match.group(1)
        for line in fm.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                key, val = key.strip(), val.strip().strip('"\'')
                if key == 'title':
                    result['title'] = val

    # 解析标题（# 开头的第一行）
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        result["title"] = title_match.group(1).strip()

    # 提取表格行
    for line in content.split('\n'):
        line = line.strip()
        if '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) >= 2:
            key, val = parts[0].lower(), parts[1]
            if '类型' in key or 'type' in key:
                result['type'] = val.strip('- ')
            elif '平台' in key or 'platform' in key:
                result['platform'] = val.strip('- ')
            elif '进度' in key or 'progress' in key:
                result['progress'] = val.strip('- ')
            elif '字' in key and ('总数' in key or '总' in key):
                try:
                    nums = re.findall(r'\d[\d,]*', val)
                    if nums:
                        result['total_chars'] = int(nums[0].replace(',', ''))
                except ValueError:
                    pass
            elif '章' in key or 'chapter' in key:
                try:
                    nums = re.findall(r'\d+', val)
                    if nums:
                        result['chapter_count'] = int(nums[0])
                except ValueError:
                    pass

    # 搜索关键信息
    date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', content)
    if date_match:
        result['last_write_date'] = date_match.group(1)

    issues_match = re.search(r'(?:待处理|待解决).*?(\d+)', content)
    if issues_match:
        result['pending_issues'] = int(issues_match.group(1))

    return result


def find_chapter_files(project_dir: str) -> list[str]:
    """查找项目中的所有章节文件."""
    base = Path(project_dir)
    patterns = ["正文/*.md", "正文/**/*.md", "chapters/*.md"]
    files = []
    for pattern in patterns:
        for f in base.glob(pattern):
            if f.name != '.gitkeep':
                files.append(str(f))
    if files:
        return sorted(files)

    # 递归搜索所有 .md 文件
    for f in sorted(base.rglob("*.md")):
        if f.name != '.gitkeep' and f.name != 'context-brief.md':
            # 优先找正文目录下的
            if '正文' in str(f) or 'chapter' in str(f).lower():
                files.append(str(f))

    return sorted(files) if files else []
