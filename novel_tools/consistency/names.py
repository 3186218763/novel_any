"""名称一致性扫描 — 角色名/称谓变异、未知人名、代词歧义."""

import re
from novel_tools.config import find_chapter_files
from novel_tools.bible.character import list_all


def scan_name_variants(text: str, known_names: list[str]) -> dict:
    """扫描文本中的名称使用情况.

    Args:
        text: 文本内容
        known_names: 已知角色名列表

    Returns:
        dict with variants, unmatched, stats
    """
    # 提取所有可能的人名（使用中文人名常见模式：2-3 字，含姓）
    # 中文常见姓氏
    SURNAMES = (
        "王李张刘陈杨黄赵周吴徐孙马胡朱郭何罗高林"
        "郑梁谢宋唐许韩冯邓曹彭曾萧田董潘袁于蒋蔡余杜叶程苏魏吕丁任沈"
        "姚卢姜崔钟谭陆汪范金石廖贾夏韦傅方白邹孟熊秦邱江尹薛闫段雷侯"
        "龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤温康施文牛樊葛邢安齐"
        "易乔伍庞颜倪庄聂章鲁岳翟殷詹申欧耿关兰焦俞左柳甘祝包宁尚符"
    )
    name_pattern = re.compile(rf'[{SURNAMES}][\u4e00-\u9fff]{{1,2}}(?![，。！？、：；""」』\)）\s])')

    found_names = name_pattern.findall(text)
    name_counts = {}
    for n in found_names:
        name_counts[n] = name_counts.get(n, 0) + 1

    # 已知角色名 vs 未知
    matched = {n: c for n, c in name_counts.items() if n in known_names}
    unmatched = {
        n: c for n, c in name_counts.items()
        if n not in known_names and c >= 2  # 至少出现 2 次才提醒
    }

    # 检查称谓变异（同角色可能用不同名字）
    # 简化版：检查是否有单个字频繁出现（可能是姓或名）
    single_chars = re.findall(rf'[{SURNAMES}](?![\u4e00-\u9fff]{{1,2}})', text)
    char_counts = {}
    for c in single_chars:
        char_counts[c] = char_counts.get(c, 0) + 1

    return {
        "matched_names": [{"name": n, "count": c} for n, c in sorted(matched.items())],
        "unmatched_names": [{"name": n, "count": c} for n, c in sorted(unmatched.items(), key=lambda x: -x[1])],
        "unmatched_count": len(unmatched),
        "total_names_found": len(found_names),
        "surname_only_refs": [{"char": c, "count": n} for c, n in sorted(char_counts.items(), key=lambda x: -x[1]) if n >= 3],
    }


def scan_pronoun_ambiguity(text: str) -> list[dict]:
    """扫描代词指代不明的情况.

    查找连续使用「他/她」的段落，可能指代不同角色。
    """
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    issues = []
    for i, para in enumerate(paragraphs):
        # 统计段落中「他」和「她」的数量
        ta_mentions = re.findall(r'[他她]', para)
        if len(ta_mentions) >= 5:
            # 检查是否有多个角色在上下文中
            names_in_para = re.findall(r'[\u4e00-\u9fff]{2,3}(?=[，。！？、；：])', para)
            unique_names = set(names_in_para)
            if len(unique_names) >= 2:
                issues.append({
                    "paragraph_index": i,
                    "pronoun_count": len(ta_mentions),
                    "characters_mentioned": list(unique_names)[:5],
                    "snippet": para[:100],
                    "detail": f"段落中 '{'他' if '他' in ta_mentions else '她'}' 出现 {len(ta_mentions)} 次，且有 {len(unique_names)} 个角色出场，可能存在指代不明",
                })

    return issues


def scan_all(project_dir: str) -> dict:
    """扫描项目所有章节的名称一致性.

    Returns:
        dict with per_chapter results
    """
    chapter_files = find_chapter_files(project_dir)
    if not chapter_files:
        return {"error": "No chapter files found", "results": []}

    results = []
    # 获取已知角色名列表
    try:
        characters = list_all(project_dir)
        known_names = [c["name"] for c in characters]
    except Exception:
        known_names = []
    for f in chapter_files:
        try:
            with open(f, encoding="utf-8") as fh:
                text = fh.read()
            variants = scan_name_variants(text, known_names)
            ambiguity = scan_pronoun_ambiguity(text)
            results.append({
                "file": f,
                "variants": variants,
                "ambiguity_issues": ambiguity,
            })
        except Exception as e:
            results.append({"file": f, "error": str(e)})

    return {"total_files": len(results), "results": results}


def _pinyin_similar(name1: str, name2: str) -> bool:
    """检测两名字是否同音异字."""
    try:
        from pypinyin import pinyin, Style
        py1 = ''.join([p[0] for p in pinyin(name1, style=Style.TONE3)])
        py2 = ''.join([p[0] for p in pinyin(name2, style=Style.TONE3)])
        return py1 == py2 and name1 != name2
    except ImportError:
        return False
