"""pipeline.db CRUD 封装 — SQLite 连接 + 表操作."""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

# pipeline.db 放在 novel_tools/../data/pipeline/ 下
PIPELINE_DIR = Path(__file__).parent.parent.parent / "data" / "pipeline"
PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = PIPELINE_DIR / "pipeline.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """确保数据库 schema 已初始化."""
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()


def get_db() -> sqlite3.Connection:
    """获取 pipeline 数据库连接."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


@contextmanager
def pipeline_session():
    """上下文管理器：自动 commit + close."""
    db = get_db()
    try:
        yield db
    finally:
        db.commit()
        db.close()


def _uid() -> str:
    return uuid.uuid4().hex[:12]


# ── books ────────────────────────────────────────────

def add_book(title: str, author: str, source_url: str, category: str = "") -> int:
    """注册新书，返回 book_id."""
    with pipeline_session() as db:
        cur = db.execute(
            "INSERT OR IGNORE INTO books (title, author, source_url, category) "
            "VALUES (?, ?, ?, ?)",
            (title, author, source_url, category),
        )
        if cur.rowcount == 0:
            row = db.execute(
                "SELECT id FROM books WHERE source_url = ?", (source_url,)
            ).fetchone()
            return row["id"]
        return cur.lastrowid


def get_book(book_id: int) -> dict | None:
    with pipeline_session() as db:
        row = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return dict(row) if row else None


def list_active_books() -> list[dict]:
    with pipeline_session() as db:
        rows = db.execute(
            "SELECT * FROM books WHERE status = 'active' "
            "ORDER BY last_analyzed_at ASC NULLS FIRST"
        ).fetchall()
        return [dict(r) for r in rows]


def mark_book_status(book_id: int, status: str) -> None:
    with pipeline_session() as db:
        db.execute("UPDATE books SET status = ? WHERE id = ?", (status, book_id))


def touch_book(book_id: int) -> None:
    with pipeline_session() as db:
        db.execute(
            "UPDATE books SET last_analyzed_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), book_id),
        )


# ── chapters ─────────────────────────────────────────

def add_chapter(
    book_id: int, chapter_no: int, title: str, file_path: str, word_count: int = 0
) -> int:
    with pipeline_session() as db:
        cur = db.execute(
            "INSERT OR IGNORE INTO chapters (book_id, chapter_no, title, file_path, word_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (book_id, chapter_no, title, file_path, word_count),
        )
        if cur.rowcount == 0:
            row = db.execute(
                "SELECT id FROM chapters WHERE file_path = ?", (file_path,)
            ).fetchone()
            return row["id"]
        return cur.lastrowid


def get_chapters(book_id: int) -> list[dict]:
    with pipeline_session() as db:
        rows = db.execute(
            "SELECT * FROM chapters WHERE book_id = ? ORDER BY chapter_no",
            (book_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── analyses ─────────────────────────────────────────

def save_analysis(
    run_id: str,
    book_id: int,
    chapter_id: int,
    module: str,
    metrics: dict,
    tool_version: str,
) -> int:
    with pipeline_session() as db:
        cur = db.execute(
            "INSERT INTO analyses (run_id, book_id, chapter_id, module, metrics, "
            "tool_version, finished_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                book_id,
                chapter_id,
                module,
                json.dumps(metrics, ensure_ascii=False),
                tool_version,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return cur.lastrowid


def get_analyses_for_chapter(chapter_id: int) -> list[dict]:
    with pipeline_session() as db:
        rows = db.execute(
            "SELECT * FROM analyses WHERE chapter_id = ? ORDER BY module",
            (chapter_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── reviews ──────────────────────────────────────────

def add_review(
    book_id: int, source: str, content: str, sentiment: str = "", keywords: str = ""
) -> int:
    with pipeline_session() as db:
        cur = db.execute(
            "INSERT INTO reviews (book_id, source, content, sentiment, keywords) "
            "VALUES (?, ?, ?, ?, ?)",
            (book_id, source, content, sentiment, keywords),
        )
        return cur.lastrowid


def get_reviews(book_id: int) -> list[dict]:
    with pipeline_session() as db:
        rows = db.execute(
            "SELECT * FROM reviews WHERE book_id = ? ORDER BY fetched_at DESC",
            (book_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── comparisons ──────────────────────────────────────

def save_comparison(
    run_id: str,
    analysis_id: int,
    review_id: int,
    dimension: str,
    matched: bool,
    confidence: float,
    verdict: str,
    gap_detail: str = "",
) -> int:
    with pipeline_session() as db:
        cur = db.execute(
            "INSERT INTO comparisons (run_id, analysis_id, review_id, dimension, "
            "matched, confidence, verdict, gap_detail) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, analysis_id, review_id, dimension, matched, confidence, verdict, gap_detail),
        )
        return cur.lastrowid


# ── gaps ─────────────────────────────────────────────

def add_gap(module: str, gap_type: str, description: str) -> int:
    """添加差距记录，相同描述会更新 occurrence_count."""
    with pipeline_session() as db:
        existing = db.execute(
            "SELECT id, occurrence_count FROM gaps "
            "WHERE module = ? AND gap_type = ? AND description = ? AND status != 'closed'",
            (module, gap_type, description),
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE gaps SET occurrence_count = ?, last_seen = ? WHERE id = ?",
                (
                    existing["occurrence_count"] + 1,
                    datetime.now(timezone.utc).isoformat(),
                    existing["id"],
                ),
            )
            return existing["id"]
        cur = db.execute(
            "INSERT INTO gaps (module, gap_type, description) VALUES (?, ?, ?)",
            (module, gap_type, description),
        )
        return cur.lastrowid


def list_open_gaps() -> list[dict]:
    with pipeline_session() as db:
        rows = db.execute(
            "SELECT * FROM gaps WHERE status = 'open' ORDER BY occurrence_count DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_gap_status(gap_id: int, status: str) -> None:
    with pipeline_session() as db:
        db.execute("UPDATE gaps SET status = ? WHERE id = ?", (status, gap_id))


# ── research ─────────────────────────────────────────

def save_research(
    gap_id: int, source: str, findings: dict, recommendation: str = ""
) -> int:
    with pipeline_session() as db:
        cur = db.execute(
            "INSERT INTO research (gap_id, source, findings, recommendation) "
            "VALUES (?, ?, ?, ?)",
            (gap_id, source, json.dumps(findings, ensure_ascii=False), recommendation),
        )
        return cur.lastrowid


# ── fixes ────────────────────────────────────────────

def save_fix(
    gap_id: int,
    branch: str,
    files_changed: list,
    tool_version_before: str,
    tool_version_after: str,
    diff_summary: str = "",
) -> int:
    with pipeline_session() as db:
        cur = db.execute(
            "INSERT INTO fixes (gap_id, branch, files_changed, diff_summary, "
            "tool_version_before, tool_version_after) VALUES (?, ?, ?, ?, ?, ?)",
            (
                gap_id,
                branch,
                json.dumps(files_changed),
                diff_summary,
                tool_version_before,
                tool_version_after,
            ),
        )
        return cur.lastrowid


def verify_fix(fix_id: int, passed: bool, improvement_metric: dict | None = None) -> None:
    with pipeline_session() as db:
        db.execute(
            "UPDATE fixes SET status = ?, verified_at = ?, improvement_metric = ? WHERE id = ?",
            (
                "passed" if passed else "failed",
                datetime.now(timezone.utc).isoformat(),
                json.dumps(improvement_metric or {}),
                fix_id,
            ),
        )
