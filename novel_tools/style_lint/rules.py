"""style_lint 规则引擎."""

import json
import re
from pathlib import Path


def _load_cheatsheet() -> dict:
    path = Path(__file__).parent / "data" / "cheatsheet_zh.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def lint(text: str, checks: list[str] | None = None,
         severity: str = "warn") -> dict:
    """对文本运行风格检查.

    Args:
        text: 文本内容
        checks: 要运行的检查列表，None=全部
        severity: 最低报告级别（ban/warn/info）
    """
    cheatsheet = _load_cheatsheet()
    severity_order = {"ban": 0, "warn": 1, "info": 2}
    min_sev = severity_order.get(severity, 1)

    all_issues = []
    available = ["redundancy", "cliche", "weasel", "adverb_abuse", "dialogue_tags"]
    active = checks if checks else available

    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text)) or 1
    lines = text.split('\n')

    for check_name in active:
        rules_list = cheatsheet.get(check_name, [])
        if isinstance(rules_list, list):
            for rule in rules_list:
                rule_sev = severity_order.get(rule.get("severity", "warn"), 1)
                if rule_sev > min_sev:
                    continue
                pattern = rule.get("pattern", "")

                if check_name in ("adverb_abuse", "dialogue_tags"):
                    count = text.count(pattern)
                    per_1k = count / (chinese_chars / 1000)
                    max_allowed = rule.get("max_per_1k", 999)
                    if per_1k > max_allowed:
                        all_issues.append({
                            "type": check_name,
                            "severity": rule["severity"],
                            "text": pattern,
                            "count": count,
                            "per_1k": round(per_1k, 1),
                            "suggestion": f"'{pattern}' \u51fa\u73b0 {count} \u6b21 ({per_1k:.1f}/\u5343\u5b57)\uff0c\u5efa\u8bae\u51cf\u81f3 {max_allowed}/\u5343\u5b57\u4ee5\u4e0b",
                            "line": -1,
                            "context": "",
                        })
                else:
                    for line_num, line_text in enumerate(lines, 1):
                        if pattern in line_text:
                            all_issues.append({
                                "type": check_name,
                                "severity": rule["severity"],
                                "text": pattern,
                                "suggestion": rule.get("suggestion", ""),
                                "line": line_num,
                                "context": line_text.strip()[:80],
                            })

    summary = {
        "total": len(all_issues),
        "ban": sum(1 for i in all_issues if i["severity"] == "ban"),
        "warn": sum(1 for i in all_issues if i["severity"] == "warn"),
        "info": sum(1 for i in all_issues if i["severity"] == "info"),
    }

    return {"issues": all_issues, "summary": summary}


def quick_scan(text: str) -> dict:
    """短文本快速启发式扫描 — 不需要 pattern 规则，纯统计.

    适用于 < 2000 字的短文本，返回额外的冗余信号。
    """
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text)) or 1
    issues = []

    # 1. 副词密度: 检测 "地" 字短语（描写过度）
    de_phrases = re.findall(r'[\u4e00-\u9fff]{1,3}地', text)
    de_density = len(de_phrases) / (chinese_chars / 100)
    if de_density > 3:
        issues.append({"type": "adverb_abuse", "severity": "warn",
                       "text": f"副词密度 {de_density:.1f}/百字",
                       "suggestion": f"'{'地'}' 短语 {len(de_phrases)} 个，描写可能过于密集"})

    # 2. 连续句首重复: 相邻句子开头相同
    sentences = [s.strip() for s in re.split(r'[。！？…]', text) if len(s.strip()) > 3]
    repeated_starts = 0
    for i in range(len(sentences) - 1):
        s1, s2 = sentences[i][:2], sentences[i+1][:2]
        if s1 == s2 and len(s1) >= 2:
            repeated_starts += 1
    if repeated_starts >= 2:
        issues.append({"type": "repetition", "severity": "warn",
                       "text": f"连续句首重复 {repeated_starts} 次",
                       "suggestion": "相邻句子开头相同，建议变换句式"})

    # 3. 感叹号密度: 网文常见水字数手段
    exclaim = text.count('！')
    exclaim_density = exclaim / (chinese_chars / 100)
    if exclaim_density > 5:
        issues.append({"type": "redundancy", "severity": "info",
                       "text": f"感叹号密度 {exclaim_density:.1f}/百字",
                       "suggestion": f"感叹号 {exclaim} 个，密度偏高"})

    # 4. 双字重复: "阵阵"、"纷纷"、"缓缓" 等
    doubled = re.findall(r'([\u4e00-\u9fff])\\1', text)
    if len(doubled) > 3:
        issues.append({"type": "redundancy", "severity": "info",
                       "text": f"叠词 {len(doubled)} 处",
                       "suggestion": f"叠词 ({','.join(set(d[:2] for d in doubled)[:5])}) 重复使用"})

    return {
        "issues": issues,
        "summary": {
            "total": len(issues),
            "ban": sum(1 for i in issues if i["severity"] == "ban"),
            "warn": sum(1 for i in issues if i["severity"] == "warn"),
            "info": sum(1 for i in issues if i["severity"] == "info"),
        },
    }
