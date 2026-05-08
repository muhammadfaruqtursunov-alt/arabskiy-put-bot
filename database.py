import sqlite3
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            lang        TEXT DEFAULT 'both',   -- 'ru', 'tj', 'both'
            reminder_time TEXT DEFAULT NULL,   -- 'HH:MM'
            current_volume  INTEGER DEFAULT 1,
            current_lesson  INTEGER DEFAULT 1,
            week_start_day  INTEGER DEFAULT 0, -- unix timestamp
            state       TEXT DEFAULT 'idle'    -- idle/study/quiz_visual/quiz_written/weekly
        );

        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            word_id     INTEGER,
            status      TEXT DEFAULT 'new',    -- new/learned/failed
            week        INTEGER DEFAULT 1,
            UNIQUE(user_id, word_id)
        );

        CREATE TABLE IF NOT EXISTS session (
            user_id     INTEGER PRIMARY KEY,
            lesson      INTEGER,
            word_index  INTEGER DEFAULT 0,     -- current word in lesson
            failures    INTEGER DEFAULT 0,
            phase       TEXT DEFAULT 'study',  -- study/visual/written
            fail_texts_index INTEGER DEFAULT 0
        );
        """)


# ── Users ──────────────────────────────────────────────

def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def create_user(user_id: int):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))


def update_user(user_id: int, **kwargs):
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {fields} WHERE user_id=?", values)


# ── Progress ────────────────────────────────────────────

def mark_word(user_id: int, word_id: int, status: str, week: int = 1):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO progress (user_id, word_id, status, week)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, word_id) DO UPDATE SET status=excluded.status
        """, (user_id, word_id, status, week))


def get_learned_words(user_id: int, week: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT word_id FROM progress
            WHERE user_id=? AND week=? AND status='learned'
        """, (user_id, week)).fetchall()
    return [r["word_id"] for r in rows]


def reset_week_progress(user_id: int, week: int):
    with get_conn() as conn:
        conn.execute("""
            UPDATE progress SET status='new'
            WHERE user_id=? AND week=?
        """, (user_id, week))


# ── Session ─────────────────────────────────────────────

def get_session(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM session WHERE user_id=?", (user_id,)).fetchone()


def set_session(user_id: int, **kwargs):
    existing = get_session(user_id)
    if existing:
        fields = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [user_id]
        with get_conn() as conn:
            conn.execute(f"UPDATE session SET {fields} WHERE user_id=?", values)
    else:
        kwargs["user_id"] = user_id
        fields = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" * len(kwargs))
        with get_conn() as conn:
            conn.execute(f"INSERT INTO session ({fields}) VALUES ({placeholders})",
                         list(kwargs.values()))


def clear_session(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM session WHERE user_id=?", (user_id,))
