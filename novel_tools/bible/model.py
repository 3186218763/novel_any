"""Story Bible 数据模型 — SQLite DDL + 连接管理."""

import sqlite3
import uuid
from pathlib import Path


def get_db(project_dir: str = ".") -> sqlite3.Connection:
    """获取 SQLite 连接，自动创建数据库和表."""
    db_path = Path(project_dir) / ".novel_tools.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """初始化数据库表结构."""
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'supporting',
            aliases TEXT DEFAULT '[]',
            profile TEXT DEFAULT '{}',
            speech_style TEXT DEFAULT '{}',
            first_appear_ch INTEGER,
            last_appear_ch INTEGER,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS world_rules (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            content TEXT NOT NULL,
            is_hard_rule INTEGER DEFAULT 0,
            first_mentioned_ch INTEGER,
            conflicts_with TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS foreshadows (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            planted_ch INTEGER NOT NULL,
            planted_scene TEXT DEFAULT '',
            resolved_ch INTEGER,
            resolved_scene TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            tags TEXT DEFAULT '[]',
            importance TEXT DEFAULT 'minor',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cooccurrence (
            char_a TEXT NOT NULL,
            char_b TEXT NOT NULL,
            chapter INT NOT NULL,
            distance INT NOT NULL,
            count INT DEFAULT 1,
            PRIMARY KEY (char_a, char_b, chapter)
        );

        CREATE INDEX IF NOT EXISTS idx_characters_name ON characters(name);
        CREATE INDEX IF NOT EXISTS idx_foreshadows_status ON foreshadows(status);
        CREATE INDEX IF NOT EXISTS idx_world_rules_category ON world_rules(category);
        CREATE INDEX IF NOT EXISTS idx_cooccurrence_chapter ON cooccurrence(chapter);
    ''')
    conn.commit()


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    """将 sqlite3.Row 转为普通 dict."""
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


from contextlib import contextmanager


@contextmanager
def bible_session(project_dir: str = "."):
    """上下文管理器：自动 commit + close 数据库连接."""
    db = get_db(project_dir)
    try:
        yield db
    finally:
        db.commit()
        db.close()
