"""角色管理 — CRUD + 出场追踪 + 不一致检测."""

import json
from novel_tools.bible.model import get_db, _uid, row_to_dict, rows_to_list


def register(project_dir: str, name: str, role: str = "supporting",
             profile: dict | None = None, speech_style: dict | None = None) -> str:
    """注册新角色，返回角色 id."""
    db = get_db(project_dir)
    char_id = _uid()
    db.execute(
        "INSERT INTO characters (id, name, role, profile, speech_style) VALUES (?, ?, ?, ?, ?)",
        (
            char_id,
            name,
            role,
            json.dumps(profile or {}, ensure_ascii=False),
            json.dumps(speech_style or {
                "patterns": [],
                "vocab_level": "中性",
                "tone": "中性",
                "catchphrases": [],
            }, ensure_ascii=False),
        ),
    )
    db.commit()
    db.close()
    return char_id


def update(project_dir: str, char_id: str, **kwargs) -> dict | None:
    """更新角色信息."""
    db = get_db(project_dir)
    allowed = {"name", "role", "aliases", "profile", "speech_style", "status"}
    updates = {}
    for k, v in kwargs.items():
        if k in allowed:
            updates[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
    if not updates:
        db.close()
        return None
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [char_id]
    db.execute(f"UPDATE characters SET {set_clause} WHERE id=?", values)
    db.commit()
    char = row_to_dict(db.execute("SELECT * FROM characters WHERE id=?", (char_id,)).fetchone())
    db.close()
    return char


def delete(project_dir: str, char_id: str) -> bool:
    """删除角色."""
    db = get_db(project_dir)
    cursor = db.execute("DELETE FROM characters WHERE id=?", (char_id,))
    db.commit()
    deleted = cursor.rowcount > 0
    db.close()
    return deleted


def get(project_dir: str, char_id: str) -> dict | None:
    """获取单个角色."""
    db = get_db(project_dir)
    result = row_to_dict(db.execute("SELECT * FROM characters WHERE id=?", (char_id,)).fetchone())
    db.close()
    return result


def list_all(project_dir: str) -> list[dict]:
    """列出所有角色."""
    db = get_db(project_dir)
    rows = db.execute("SELECT * FROM characters ORDER BY name").fetchall()
    db.close()
    return rows_to_list(rows)


def track_appearance(project_dir: str, char_id: str, chapter_num: int) -> None:
    """记录角色出场章节."""
    db = get_db(project_dir)
    char = db.execute("SELECT first_appear_ch, last_appear_ch FROM characters WHERE id=?", (char_id,)).fetchone()
    if char:
        first = char["first_appear_ch"] if char["first_appear_ch"] else chapter_num
        last = max(char["last_appear_ch"] or 0, chapter_num)
        db.execute(
            "UPDATE characters SET first_appear_ch=?, last_appear_ch=? WHERE id=?",
            (first, last, char_id),
        )
    db.commit()
    db.close()


def detect_inconsistencies(project_dir: str) -> list[dict]:
    """检测角色数据中的不一致（同名、别名冲突等）."""
    db = get_db(project_dir)
    rows = db.execute("SELECT * FROM characters ORDER BY name").fetchall()
    db.close()

    issues = []
    names_seen = {}

    for r in rows:
        char = dict(r)
        name = char["name"]
        if name in names_seen:
            issues.append({
                "type": "duplicate_name",
                "characters": [names_seen[name], char["id"]],
                "detail": f"角色名重复: {name}",
            })
        names_seen[name] = char["id"]

    return issues
