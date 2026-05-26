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
