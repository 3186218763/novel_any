"""角色管理 — CRUD + 出场追踪 + 不一致检测."""

import json
from novel_tools.bible.model import get_db, _uid, row_to_dict, rows_to_list


def register(project_dir: str, name: str, role: str = "supporting",
             profile: dict | None = None, speech_style: dict | None = None) -> str:
    """注册新角色，返回角色 id."""
    from novel_tools.bible.model import bible_session
    char_id = _uid()
    with bible_session(project_dir) as db:
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
    return char_id


def update(project_dir: str, char_id: str, **kwargs) -> dict | None:
    """更新角色信息."""
    from novel_tools.bible.model import bible_session
    allowed = {"name", "role", "aliases", "profile", "speech_style", "status"}
    updates = {}
    for k, v in kwargs.items():
        if k in allowed:
            updates[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
    if not updates:
        return None
    with bible_session(project_dir) as db:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [char_id]
        db.execute(f"UPDATE characters SET {set_clause} WHERE id=?", values)
        char = row_to_dict(db.execute("SELECT * FROM characters WHERE id=?", (char_id,)).fetchone())
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


def normalize_aliases(project_dir: str) -> list[dict]:
    """检测可能的别名/同一人物."""
    from novel_tools.bible.model import bible_session
    results = []
    with bible_session(project_dir) as db:
        chars = db.execute("SELECT id, name FROM characters WHERE status='active'").fetchall()
    chars = [dict(c) for c in chars]

    for i, a in enumerate(chars):
        for j, b in enumerate(chars):
            if j <= i:
                continue
            score = 0
            if a["name"] and b["name"] and a["name"][0] == b["name"][0]:
                score += 40
            a_set = set(a["name"][1:]) if len(a["name"]) > 1 else set()
            b_set = set(b["name"][1:]) if len(b["name"]) > 1 else set()
            if a_set & b_set:
                score += min(len(a_set & b_set) * 15, 30)
            len_diff = abs(len(a["name"]) - len(b["name"]))
            if len_diff <= 1:
                score += 10
            if score >= 50:
                results.append({
                    "candidates": [a["id"], b["id"]],
                    "names": [a["name"], b["name"]],
                    "confidence": round(score / 100, 2),
                    "suggestion": "merge" if score >= 70 else "review",
                })
    return sorted(results, key=lambda x: x["confidence"], reverse=True)


def build_relation_graph(project_dir: str) -> dict:
    """构建角色关系网络."""
    from novel_tools.bible.model import bible_session

    nodes = []
    with bible_session(project_dir) as db:
        chars = db.execute(
            "SELECT id, name, role, first_appear_ch, last_appear_ch FROM characters WHERE status='active'"
        ).fetchall()
        for c in chars:
            nodes.append({
                "id": c["id"], "name": c["name"], "role": c["role"], "degree": 0,
            })
        cooc = db.execute("SELECT char_a, char_b, chapter, count FROM cooccurrence").fetchall()

    edges = []
    degree_map: dict[str, int] = {n["id"]: 0 for n in nodes}
    for row in cooc:
        a, b = row["char_a"], row["char_b"]
        edges.append({
            "from": a, "to": b, "weight": row["count"],
            "chapters": [row["chapter"]],
        })
        degree_map[a] = degree_map.get(a, 0) + row["count"]
        degree_map[b] = degree_map.get(b, 0) + row["count"]

    merged: dict[tuple, dict] = {}
    for e in edges:
        key = tuple(sorted([e["from"], e["to"]]))
        if key in merged:
            merged[key]["weight"] += e["weight"]
            merged[key]["chapters"].extend(e["chapters"])
        else:
            merged[key] = e
    edges = list(merged.values())

    for n in nodes:
        n["degree"] = degree_map.get(n["id"], 0)

    return {"nodes": nodes, "edges": edges}
