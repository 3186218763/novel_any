-- pipeline.db schema for novel_auto_pipeline

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    source_url TEXT UNIQUE,
    category TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_analyzed_at TIMESTAMP,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER REFERENCES books(id),
    chapter_no INTEGER NOT NULL,
    title TEXT,
    file_path TEXT UNIQUE,
    word_count INTEGER DEFAULT 0,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    book_id INTEGER REFERENCES books(id),
    chapter_id INTEGER REFERENCES chapters(id),
    tool_version TEXT,
    module TEXT NOT NULL,
    metrics JSON,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER REFERENCES books(id),
    source TEXT,
    content TEXT NOT NULL,
    sentiment TEXT,
    keywords TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    analysis_id INTEGER REFERENCES analyses(id),
    review_id INTEGER REFERENCES reviews(id),
    dimension TEXT,
    matched BOOLEAN,
    confidence REAL DEFAULT 0.0,
    verdict TEXT,
    gap_detail TEXT,
    compared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT NOT NULL,
    gap_type TEXT,
    description TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    occurrence_count INTEGER DEFAULT 1,
    status TEXT DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gap_id INTEGER REFERENCES gaps(id),
    source TEXT,
    findings JSON,
    recommendation TEXT,
    researched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fixes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gap_id INTEGER REFERENCES gaps(id),
    pr_url TEXT,
    branch TEXT,
    files_changed JSON,
    diff_summary TEXT,
    tool_version_before TEXT,
    tool_version_after TEXT,
    verified_at TIMESTAMP,
    improvement_metric JSON,
    status TEXT DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_chapters_book ON chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_analyses_run ON analyses(run_id);
CREATE INDEX IF NOT EXISTS idx_analyses_module ON analyses(module);
CREATE INDEX IF NOT EXISTS idx_comparisons_run ON comparisons(run_id);
CREATE INDEX IF NOT EXISTS idx_gaps_module ON gaps(module);
CREATE INDEX IF NOT EXISTS idx_gaps_status ON gaps(status);
