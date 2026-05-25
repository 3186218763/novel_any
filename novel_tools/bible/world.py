"""世界观规则管理 — CRUD + 冲突检测."""

import json
import re
from novel_tools.bible.model import get_db, _uid, rows_to_list


def register_rule(project_dir: str, category: str, key: str, content: str,
                  is_hard_rule: bool = False, chapter: int | None = None) -> str:
    """注册世界观规则，返回 id."""
    db = get_db(project_dir)
    rule_id = _uid()
    db.execute(
        "INSERT INTO world_rules (id, category, key, content, is_hard_rule, first_mentioned_ch) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (rule_id, category, key, content, 1 if is_hard_rule else 0, chapter),
    )
    db.commit()
    db.close()
    return rule_id


def list_rules(project_dir: str, category: str | None = None) -> list[dict]:
    """列出世界观规则，可按分类过滤."""
    db = get_db(project_dir)
    if category:
        rows = db.execute(
            "SELECT * FROM world_rules WHERE category=? ORDER BY key", (category,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM world_rules ORDER BY category, key").fetchall()
    db.close()
    return rows_to_list(rows)


def get_hard_rules(project_dir: str) -> list[dict]:
    """获取所有硬规则."""
    db = get_db(project_dir)
    rows = db.execute(
        "SELECT * FROM world_rules WHERE is_hard_rule=1 ORDER BY category, key"
    ).fetchall()
    db.close()
    return rows_to_list(rows)


def update_rule(project_dir: str, rule_id: str, **kwargs) -> dict | None:
    """更新规则."""
    db = get_db(project_dir)
    allowed = {"category", "key", "content", "is_hard_rule", "first_mentioned_ch"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        db.close()
        return None
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [rule_id]
    db.execute(f"UPDATE world_rules SET {set_clause} WHERE id=?", values)
    db.commit()
    row = db.execute("SELECT * FROM world_rules WHERE id=?", (rule_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def delete_rule(project_dir: str, rule_id: str) -> bool:
    """删除规则."""
    db = get_db(project_dir)
    cursor = db.execute("DELETE FROM world_rules WHERE id=?", (rule_id,))
    db.commit()
    deleted = cursor.rowcount > 0
    db.close()
    return deleted


def check_conflicts(project_dir: str, new_content: str) -> list[dict]:
    """简单关键词冲突检测：检查新规则是否与已有硬规则冲突.

    注：这是一个启发式方法，复杂冲突需要 LLM 判断。
    """
    db = get_db(project_dir)
    hard_rules = db.execute(
        "SELECT * FROM world_rules WHERE is_hard_rule=1"
    ).fetchall()
    db.close()

    # 提取新内容的否定/矛盾关键词
    negation_patterns = ["不", "并非", "不是", "没有", "禁止", "无法", "不可"]
    has_negation = any(p in new_content for p in negation_patterns)

    conflicts = []
    for rule in hard_rules:
        r = dict(rule)
        # 简单检查：如果新内容有否定词但主题关键词重叠 → 可能存在冲突
        # 提取关键词（2-5字词组）进行比较，避免逐字集合的误报
        content_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,5}', new_content))
        rule_keywords = set(re.findall(r'[\u4e00-\u9fff]{2,5}', r["content"]))
        overlap = content_keywords & rule_keywords
        if len(overlap) > 3 and has_negation:
            conflicts.append({
                "rule_id": r["id"],
                "key": r["key"],
                "category": r["category"],
                "content": r["content"][:100],
                "overlap_chars": len(overlap),
                "detail": "新内容包含否定词且与已有硬规则关键词高度重叠",
            })

    return conflicts
