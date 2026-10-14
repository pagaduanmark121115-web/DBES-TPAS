"""DBES TPAS - shared database helper (Turso with local SQLite fallback)."""
import sqlite3
import streamlit as st

SECTIONS = [
    "A. Knowledge of Subject & Teaching Style",
    "B. Interest and Stimulation",
    "C. Class Management and Organization",
    "D. Teacher-Student Relations",
]

SCALE = {5: "Consistently", 4: "Frequently", 3: "Occasionally", 2: "Rarely", 1: "Very Rarely"}

# The 28 statements of TPAS Form 6 (Student Evaluation of Teachers)
SEED = {
    SECTIONS[0]: [
        "has very good knowledge of the subject he/she teaches.",
        "is organized and prepared for class.",
        "uses learning materials like power point presentations, pictures, charts, illustrations, etc. to help students understand the lesson.",
        "presents the lesson in an understandable way.",
        "uses clear examples and emphasizes important points in the lesson.",
        "adjusts her ways of teaching to the students' learning abilities.",
    ],
    SECTIONS[1]: [
        "shows enthusiasm about the subject he teaches.",
        "helps student to think independently.",
        "uses a variety of teaching styles and techniques.",
        "makes sure that class lessons and discussions are interesting, enjoyable, worthwhile and challenging.",
        "lets students tell him/her what they think or feel about the lesson.",
        "gives favorable and encouraging comments when students give correct answers or good ideas.",
    ],
    SECTIONS[2]: [
        "speaks fluently and clearly.",
        "starts and ends classes on time.",
        "establishes clear guidelines for quizzes, tests and papers.",
        "promptly informs the students of the results of tests and assignments.",
        "grades students fairly, based on how much they have actually learned or done.",
        "sees to it that all students obey school rules and regulations.",
        "maintains a reasonable level of order and discipline in class.",
        "makes sure that the classroom is always clean and orderly, shows proper care for school property.",
    ],
    SECTIONS[3]: [
        "makes the students feel free to ask questions.",
        "is fair in dealing with students.",
        "is available to students for guidance and assistance even outside class time.",
        "shows a personal interest in students' progress and success.",
        "reminds students about proper behavior at all times.",
        "is pleasant, patient, amiable and mild tempered.",
        "reminds students to show respect and care for other people.",
        "reminds students of their responsibilities as good and worthy members of the community.",
    ],
}

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS tpas_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section TEXT NOT NULL,
        statement TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS tpas_evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sy TEXT NOT NULL,
        school TEXT,
        teacher_name TEXT NOT NULL,
        comment_strategy TEXT,
        comment_classroom TEXT,
        comment_others TEXT,
        submitted_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS tpas_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evaluation_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        rating INTEGER NOT NULL
    )""",
]


@st.cache_resource
def _conn():
    """Use Turso if secrets exist; otherwise a local SQLite file (testing only)."""
    try:
        import libsql_experimental as libsql

        url = st.secrets["TURSO_DATABASE_URL"]
        token = st.secrets["TURSO_AUTH_TOKEN"]
        conn = libsql.connect("tpas_replica.db", sync_url=url, auth_token=token)
        conn.sync()
        return conn, True
    except Exception:
        return sqlite3.connect("tpas_local.db", check_same_thread=False), False


def using_turso() -> bool:
    return _conn()[1]


def run(sql, params=()):
    """SELECT -> list of dicts."""
    conn, _ = _conn()
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def write(statements):
    """Run a list of (sql, params) in one transaction."""
    conn, remote = _conn()
    for sql, params in statements:
        conn.execute(sql, params)
    conn.commit()
    if remote:
        conn.sync()


@st.cache_resource
def init_db():
    write([(s, ()) for s in SCHEMA])
    if run("SELECT COUNT(*) AS n FROM tpas_questions")[0]["n"] == 0:
        stmts = []
        for section, items in SEED.items():
            for i, text in enumerate(items, start=1):
                stmts.append(
                    ("INSERT INTO tpas_questions (section, statement, sort_order) VALUES (?, ?, ?)",
                     (section, text, i))
                )
        write(stmts)
    return True


def require_admin():
    """Simple password gate for admin pages. Set ADMIN_PASSWORD in secrets."""
    try:
        pw = st.secrets["ADMIN_PASSWORD"]
    except Exception:
        pw = None
    if not pw:
        st.warning("No ADMIN_PASSWORD set in secrets - this page is unprotected.")
        return
    if st.session_state.get("is_admin"):
        return
    entered = st.text_input("Admin password", type="password")
    if st.button("Login"):
        if entered == pw:
            st.session_state["is_admin"] = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()
