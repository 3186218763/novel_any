"""伏笔管理 — 埋点/回收/预警/自动扫描."""

import json
import re
from novel_tools.bible.model import get_db, _uid, rows_to_list


def plant(project_dir: str, description: str, chapter: int,
          tags: list[str] | None = None, importance: str = "minor") -> str:
    """埋入新伏笔，返回 id."""
    db = get_db(project_dir)
    fs_id = _uid()
    db.execute(
        "INSERT INTO foreshadows (id, description, planted_ch, tags, importance) VALUES (?, ?, ?, ?, ?)",
        (fs_id, description, chapter, json.dumps(tags or [], ensure_ascii=False), importance),
    )
    db.commit()
    db.close()
    return fs_id


def resolve(project_dir: str, fs_id: str, chapter: int) -> bool:
    """回收伏笔."""
    db = get_db(project_dir)
    cursor = db.execute(
        "UPDATE foreshadows SET status='resolved', resolved_ch=? WHERE id=?",
        (chapter, fs_id),
    )
    db.commit()
    updated = cursor.rowcount > 0
    db.close()
    return updated


def list_unresolved(project_dir: str) -> list[dict]:
    """列出所有未回收的伏笔."""
    db = get_db(project_dir)
    rows = db.execute(
        "SELECT * FROM foreshadows WHERE status='pending' ORDER BY planted_ch"
    ).fetchall()
    db.close()
    return rows_to_list(rows)


def list_all(project_dir: str) -> list[dict]:
    """列出所有伏笔."""
    db = get_db(project_dir)
    rows = db.execute("SELECT * FROM foreshadows ORDER BY planted_ch").fetchall()
    db.close()
    return rows_to_list(rows)


def warn_expiring(project_dir: str, threshold_ch: int = 5,
                  current_chapter: int | None = None) -> list[dict]:
    """预警：距埋入已超过 threshold 章仍未回收的伏笔.

    Args:
        threshold_ch: 超过此章数未回收则预警
        current_chapter: 当前写作进度（章节号），若不提供则从 characters 表推算
    """
    db = get_db(project_dir)
    rows = db.execute(
        "SELECT * FROM foreshadows WHERE status='pending' ORDER BY planted_ch"
    ).fetchall()

    # 确定当前章节号：优先用传入参数，否则从 characters 表推算
    if current_chapter is None:
        try:
            max_ch_row = db.execute(
                "SELECT MAX(last_appear_ch) as max_ch FROM characters"
            ).fetchone()
            current_chapter = max_ch_row["max_ch"] if max_ch_row and max_ch_row["max_ch"] else 0
        except Exception:
            current_chapter = 0
        # 如果 characters 表也没有数据，回退到伏笔表中最大 planted_ch
        if current_chapter == 0:
            for r in rows:
                planted = r["planted_ch"]
                if planted > current_chapter:
                    current_chapter = planted
    db.close()

    # 检查哪些伏笔超过了阈值章数
    warnings = []
    for r in rows:
        ch = r["planted_ch"]
        age = current_chapter - ch
        if age >= threshold_ch:
            d = dict(r)
            d["age_chapters"] = age
            d["warning"] = f"伏笔已埋 {age} 章未回收"
            warnings.append(d)

    return warnings


def scan_auto(text: str) -> list[str]:
    """启发式扫描文本中的潜在伏笔句.

    匹配模式：
    - 「他不知道的是...」「他不知道...」→ 信息差
    - 「此刻他还不明白...」「他还不知道...」→ 未来揭示
    - 「后来他才明白...」「多年后回想...」→ 前后呼应
    - 「这似乎是...」「隐隐觉得...」「莫名感到...」→ 预兆
    """
    patterns = [
        r'(?:他|她|它|谁|没人).{0,5}(?:不知道|没想到|没料到|没察觉).{3,}',
        r'(?:此刻|这时|当时).{0,5}(?:还不|尚不|未曾).{2,}(?:知道|明白|察觉|发现)',
        r'(?:后来|多年后|很久以后).{0,5}(?:才|终于|回想起)',
        r'(?:似乎|仿佛|隐隐|莫名|隐隐约约).{2,}(?:觉得|感到|感觉|察觉到)',
        r'这.{0,3}(?:似乎|好像|仿佛|可能|大概).{3,}',
        r'如果.{0,3}(?:知道|明白|看到).{3,}',
    ]

    candidates = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            if len(m) > 5 and m not in candidates:
                candidates.append(m.strip())

    return candidates[:10]  # 最多返回 10 个
