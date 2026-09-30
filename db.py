"""Database layer: Turso (libsql) in production, local SQLite for development.

API used by the rest of the app:
    db.query(sql, args)   -> list[dict]
    db.execute(sql, args) -> last inserted row id (or None)
    db.batch([(sql, args), ...]) -> runs all statements atomically
"""
import os
import sqlite3
import threading

_LOCK = threading.RLock()
_DB = None
_READY = False

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        pw_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grade_level TEXT NOT NULL,
        name TEXT NOT NULL,
        enrolled INTEGER NOT NULL DEFAULT 0,
        UNIQUE (grade_level, name)
    )""",
    """CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    )""",
    # One row per teacher + grade level + subject (+ component, e.g. Life and Career Skills: Physical Education)
    """CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        teacher_id INTEGER NOT NULL,
        grade_level TEXT NOT NULL,
        subject TEXT NOT NULL,
        component TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT,
        UNIQUE (teacher_id, grade_level, subject, component)
    )""",
    """CREATE TABLE IF NOT EXISTS assignment_sections (
        assignment_id INTEGER NOT NULL,
        section_id INTEGER NOT NULL,
        PRIMARY KEY (assignment_id, section_id)
    )""",
    # Answers are anonymous: random id, date only, no email, no time of day.
    """CREATE TABLE IF NOT EXISTS responses (
        id TEXT PRIMARY KEY,
        assignment_id INTEGER NOT NULL,
        school_year TEXT NOT NULL,
        semester TEXT NOT NULL,
        section_id INTEGER,
        section_name TEXT,
        submitted_date TEXT,
        comment_strategy TEXT DEFAULT '',
        comment_management TEXT DEFAULT '',
        comment_others TEXT DEFAULT '',
        form_version TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS response_ratings (
        response_id TEXT NOT NULL,
        item_no INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        PRIMARY KEY (response_id, item_no)
    )""",
    # Email (hashed) is kept ONLY to block duplicate submissions. Not linked to any response.
    """CREATE TABLE IF NOT EXISTS respondents (
        assignment_id INTEGER NOT NULL,
        school_year TEXT NOT NULL,
        semester TEXT NOT NULL,
        email_hash TEXT NOT NULL,
        PRIMARY KEY (assignment_id, school_year, semester, email_hash)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_resp_assign ON responses (assignment_id, school_year, semester)",
]


def secret(name, default=""):
    """Read a setting from environment variables, then Streamlit secrets."""
    v = os.environ.get(name)
    if v:
        return v
    try:
        import streamlit as st
        v = st.secrets.get(name, default)
        return v if v else default
    except Exception:
        return default


class _Local:
    name = "Local SQLite (development only - data is NOT permanent on Streamlit Cloud)"
    is_local = True

    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def query(self, sql, args=()):
        with _LOCK:
            cur = self.conn.execute(sql, tuple(args))
            rows = [dict(r) for r in cur.fetchall()]
            self.conn.commit()
            return rows

    def execute(self, sql, args=()):
        with _LOCK:
            cur = self.conn.execute(sql, tuple(args))
            self.conn.commit()
            return cur.lastrowid

    def batch(self, stmts):
        with _LOCK:
            try:
                for sql, args in stmts:
                    self.conn.execute(sql, tuple(args))
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise


class _Turso:
    name = "Turso"
    is_local = False

    def __init__(self, url, token):
        import libsql_client
        self._lc = libsql_client
        url = url.strip()
        # libsql:// makes the client use a websocket that Turso often rejects (HTTP 400);
        # https:// is the reliable scheme.
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://"):]
        self.client = libsql_client.create_client_sync(url, auth_token=token)

    def query(self, sql, args=()):
        with _LOCK:
            rs = self.client.execute(sql, list(args))
            cols = list(rs.columns)
            return [{c: row[i] for i, c in enumerate(cols)} for row in rs.rows]

    def execute(self, sql, args=()):
        with _LOCK:
            rs = self.client.execute(sql, list(args))
            return getattr(rs, "last_insert_rowid", None)

    def _stmt(self, sql, args):
        S = getattr(self._lc, "Statement", None)
        return S(sql, list(args)) if S else (sql, list(args))

    def batch(self, stmts):
        with _LOCK:
            self.client.batch([self._stmt(s, a) for s, a in stmts])


def get_db():
    global _DB
    if _DB is None:
        with _LOCK:
            if _DB is None:
                url = secret("TURSO_DATABASE_URL")
                token = secret("TURSO_AUTH_TOKEN")
                if url:
                    _DB = _Turso(url, token)
                else:
                    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tpas_local.db")
                    _DB = _Local(os.environ.get("TPAS_LOCAL_DB", path))
    return _DB


def init():
    """Create tables if missing (runs once per server process)."""
    global _READY
    if _READY:
        return
    d = get_db()
    for stmt in SCHEMA:
        d.execute(stmt)
    _READY = True


def backend_name():
    return get_db().name


def is_local():
    return get_db().is_local


def query(sql, args=()):
    return get_db().query(sql, args)


def execute(sql, args=()):
    return get_db().execute(sql, args)


def batch(stmts):
    return get_db().batch(stmts)
