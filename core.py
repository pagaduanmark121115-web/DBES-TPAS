"""Business logic (no Streamlit imports, so it can be tested on its own)."""
import hashlib
import hmac
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

import db
from tpas_form import (CAT_CODES, CAT_NAME, CAT_SHORT, COMMENT_FIELDS, FORM_CODE,
                       GRADE_LEVELS, ITEM_CAT, ITEM_NUMBERS, ITEM_TEXT, SEMESTERS)

PH_TZ = timezone(timedelta(hours=8))
TOKEN_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L
DEFAULTS = {"school_year": "", "evaluation_open": "1", "allowed_domains": "",
            "overall_method": "category", "email_salt": ""}


def now_str():
    return datetime.now(PH_TZ).strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ settings
def get_setting(key, default=None):
    rows = db.query("SELECT value FROM settings WHERE key=?", (key,))
    if rows and rows[0]["value"] is not None:
        return rows[0]["value"]
    return DEFAULTS.get(key, "") if default is None else default


def set_setting(key, value):
    db.execute("INSERT INTO settings(key,value) VALUES(?,?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def base_url():
    return (db.secret("APP_BASE_URL") or "http://localhost:8501").strip().rstrip("/")


def build_link(token):
    return f"{base_url()}/evaluate?t={token}"


# --------------------------------------------------------------------- users
def _pw_hash(password, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000).hex()


def any_user():
    return db.query("SELECT COUNT(*) AS n FROM users")[0]["n"] > 0


def create_user(username, password):
    username = (username or "").strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters."
    salt = secrets.token_hex(16)
    try:
        db.execute("INSERT INTO users(username,pw_hash,salt,created_at) VALUES(?,?,?,?)",
                   (username, _pw_hash(password, salt), salt, now_str()))
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return False, "That username already exists."
        raise
    return True, "Account created."


def verify_user(username, password):
    rows = db.query("SELECT username,pw_hash,salt FROM users WHERE username=?", ((username or "").strip(),))
    if not rows:
        return False
    return hmac.compare_digest(rows[0]["pw_hash"], _pw_hash(password or "", rows[0]["salt"]))


def change_password(username, new_password):
    if len(new_password or "") < 8:
        return False, "Password must be at least 8 characters."
    salt = secrets.token_hex(16)
    db.execute("UPDATE users SET pw_hash=?, salt=? WHERE username=?",
               (_pw_hash(new_password, salt), salt, username))
    return True, "Password updated."


# ------------------------------------------------------------------ sections
def add_section(grade, name, enrolled):
    name = (name or "").strip()
    if not name:
        return False, "Section name is required."
    try:
        db.execute("INSERT INTO sections(grade_level,name,enrolled) VALUES(?,?,?)",
                   (grade, name, int(enrolled or 0)))
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return False, "That section already exists for this grade level."
        raise
    return True, "Section added."


def list_sections(grade=None):
    if grade:
        return db.query("SELECT * FROM sections WHERE grade_level=? ORDER BY name", (grade,))
    return db.query("SELECT * FROM sections ORDER BY grade_level, name")


def update_section(section_id, name, enrolled):
    db.execute("UPDATE sections SET name=?, enrolled=? WHERE id=?",
               ((name or "").strip(), int(enrolled or 0), section_id))


def delete_section(section_id):
    used = db.query("SELECT COUNT(*) AS n FROM assignment_sections WHERE section_id=?", (section_id,))[0]["n"]
    if used:
        return False, "This section is used by an assignment. Remove it from the assignment first."
    db.execute("DELETE FROM sections WHERE id=?", (section_id,))
    return True, "Section deleted."


# ------------------------------------------------------------------ teachers
def add_teacher(name):
    name = " ".join((name or "").split())
    if not name:
        return False, "Teacher name is required."
    try:
        db.execute("INSERT INTO teachers(name,active) VALUES(?,1)", (name,))
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return False, "A teacher with that name already exists."
        raise
    return True, "Teacher added."


def list_teachers(active_only=False):
    sql = "SELECT * FROM teachers" + (" WHERE active=1" if active_only else "") + " ORDER BY name"
    return db.query(sql)


def rename_teacher(teacher_id, name):
    name = " ".join((name or "").split())
    if not name:
        return False, "Teacher name is required."
    try:
        db.execute("UPDATE teachers SET name=? WHERE id=?", (name, teacher_id))
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return False, "A teacher with that name already exists."
        raise
    return True, "Teacher updated."


def set_teacher_active(teacher_id, active):
    db.execute("UPDATE teachers SET active=? WHERE id=?", (1 if active else 0, teacher_id))


# --------------------------------------------------------------- assignments
def subject_label(subject, component):
    return f"{subject}: {component}" if component else subject


def _new_token():
    while True:
        t = "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(8))
        if not db.query("SELECT 1 AS x FROM assignments WHERE token=?", (t,)):
            return t


def create_assignment(teacher_id, grade, subject, component, section_ids):
    subject = " ".join((subject or "").split())
    component = " ".join((component or "").split())
    if not subject:
        return False, "Subject is required."
    if not section_ids:
        return False, "Select at least one section."
    token = _new_token()
    try:
        aid = db.execute(
            "INSERT INTO assignments(token,teacher_id,grade_level,subject,component,active,created_at) "
            "VALUES(?,?,?,?,?,1,?)", (token, teacher_id, grade, subject, component, now_str()))
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return False, "This teacher already has that subject for this grade level."
        raise
    db.batch([("INSERT INTO assignment_sections(assignment_id,section_id) VALUES(?,?)", (aid, s))
              for s in section_ids])
    return True, token


def update_assignment(assignment_id, subject, component, section_ids, active):
    subject = " ".join((subject or "").split())
    component = " ".join((component or "").split())
    if not subject:
        return False, "Subject is required."
    if not section_ids:
        return False, "Select at least one section."
    try:
        db.execute("UPDATE assignments SET subject=?, component=?, active=? WHERE id=?",
                   (subject, component, 1 if active else 0, assignment_id))
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return False, "This teacher already has that subject for this grade level."
        raise
    stmts = [("DELETE FROM assignment_sections WHERE assignment_id=?", (assignment_id,))]
    stmts += [("INSERT INTO assignment_sections(assignment_id,section_id) VALUES(?,?)", (assignment_id, s))
              for s in section_ids]
    db.batch(stmts)
    return True, "Assignment updated."


def delete_assignment(assignment_id):
    n = db.query("SELECT COUNT(*) AS n FROM responses WHERE assignment_id=?", (assignment_id,))[0]["n"]
    if n:
        return False, f"This assignment already has {n} response(s). Deactivate it instead of deleting."
    db.batch([("DELETE FROM assignment_sections WHERE assignment_id=?", (assignment_id,)),
              ("DELETE FROM assignments WHERE id=?", (assignment_id,))])
    return True, "Assignment deleted."


def list_assignments():
    rows = db.query(
        "SELECT a.id, a.token, a.teacher_id, t.name AS teacher_name, a.grade_level, a.subject, "
        "a.component, a.active, t.active AS teacher_active, "
        "(SELECT COUNT(*) FROM responses r WHERE r.assignment_id=a.id) AS n_responses "
        "FROM assignments a JOIN teachers t ON t.id=a.teacher_id "
        "ORDER BY t.name, a.grade_level, a.subject, a.component")
    secs = db.query("SELECT x.assignment_id, s.id, s.name FROM assignment_sections x "
                    "JOIN sections s ON s.id=x.section_id ORDER BY s.name")
    by = {}
    for s in secs:
        by.setdefault(s["assignment_id"], []).append({"id": s["id"], "name": s["name"]})
    for r in rows:
        r["sections"] = by.get(r["id"], [])
        r["label"] = subject_label(r["subject"], r["component"])
    return rows


def get_assignment_by_token(token):
    rows = db.query(
        "SELECT a.*, t.name AS teacher_name, t.active AS teacher_active FROM assignments a "
        "JOIN teachers t ON t.id=a.teacher_id WHERE a.token=?", ((token or "").strip().upper(),))
    if not rows:
        return None
    a = rows[0]
    a["label"] = subject_label(a["subject"], a["component"])
    return a


def assignment_sections(assignment_id):
    return db.query("SELECT s.id, s.name, s.enrolled FROM assignment_sections x "
                    "JOIN sections s ON s.id=x.section_id WHERE x.assignment_id=? ORDER BY s.name",
                    (assignment_id,))


# ------------------------------------------------------------- email / spam
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-']+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def normalize_email(email):
    return (email or "").strip().lower()


def is_valid_email(email):
    return bool(EMAIL_RE.match(email or ""))


def allowed_domains():
    return [d.strip().lower().lstrip("@") for d in get_setting("allowed_domains", "").split(",") if d.strip()]


def domain_allowed(email):
    doms = allowed_domains()
    if not doms:
        return True
    dom = email.rsplit("@", 1)[-1]
    return any(dom == d or dom.endswith("." + d) for d in doms)


def _salt():
    s = db.secret("EMAIL_HASH_SALT")
    if s:
        return s
    s = get_setting("email_salt", "")
    if not s:
        s = secrets.token_hex(32)
        set_setting("email_salt", s)
    return s


def hash_email(email):
    return hmac.new(_salt().encode(), normalize_email(email).encode(), hashlib.sha256).hexdigest()


def is_low_effort(text):
    t = re.sub(r"\s+", "", (text or "").strip().lower())
    if not t:
        return False
    return len(t) < 3 or (len(t) >= 4 and len(set(t)) <= 2)


# --------------------------------------------------------------- submission
def submit_response(token, semester, section_id, email, ratings, comments):
    """Validate and save one anonymous evaluation. Returns (ok, message)."""
    if get_setting("evaluation_open", "1") != "1":
        return False, "Evaluations are currently closed."
    sy = get_setting("school_year", "").strip()
    if not sy:
        return False, "The school year has not been set yet. Please contact HR."
    a = get_assignment_by_token(token)
    if not a or not a["active"] or not a["teacher_active"]:
        return False, "This evaluation link is no longer active."
    if semester not in SEMESTERS:
        return False, "Please select the semester."
    secs = {s["id"]: s for s in assignment_sections(a["id"])}
    if section_id not in secs:
        return False, "Please select your section."
    email = normalize_email(email)
    if not is_valid_email(email):
        return False, "Please enter a valid email address."
    if not domain_allowed(email):
        doms = ", ".join("@" + d for d in allowed_domains())
        return False, f"Please use your school email address ({doms})."
    missing = [n for n in ITEM_NUMBERS if ratings.get(n) not in (1, 2, 3, 4, 5)]
    if missing:
        return False, "Please rate every statement. Unanswered: " + ", ".join(str(n) for n in missing)
    clean = {}
    for col, label in COMMENT_FIELDS:
        text = (comments.get(col) or "").strip()
        if is_low_effort(text):
            return False, f"Please write a meaningful comment for \u201c{label}\u201d or leave it blank."
        clean[col] = text
    h = hash_email(email)
    if db.query("SELECT 1 AS x FROM respondents WHERE assignment_id=? AND school_year=? AND semester=? "
                "AND email_hash=?", (a["id"], sy, semester, h)):
        return False, "You have already evaluated this teacher and subject for this semester."
    rid = str(uuid.uuid4())
    stmts = [
        ("INSERT INTO respondents(assignment_id,school_year,semester,email_hash) VALUES(?,?,?,?)",
         (a["id"], sy, semester, h)),
        ("INSERT INTO responses(id,assignment_id,school_year,semester,section_id,section_name,"
         "submitted_date,comment_strategy,comment_management,comment_others,form_version) "
         "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
         (rid, a["id"], sy, semester, section_id, secs[section_id]["name"],
          datetime.now(PH_TZ).date().isoformat(), clean["comment_strategy"],
          clean["comment_management"], clean["comment_others"], FORM_CODE)),
    ]
    stmts += [("INSERT INTO response_ratings(response_id,item_no,rating) VALUES(?,?,?)", (rid, n, ratings[n]))
              for n in ITEM_NUMBERS]
    try:
        db.batch(stmts)
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            return False, "You have already evaluated this teacher and subject for this semester."
        return False, "Sorry, your evaluation could not be saved. Please try again."
    return True, "Thank you! Your evaluation was submitted."


# ------------------------------------------------------------------- scoring
def r2(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt(x):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else f"{r2(x):.2f}"


def band(avg):
    v = r2(avg)
    if v >= Decimal("4.50"):
        return "Outstanding"
    if v >= Decimal("4.00"):
        return "Very Satisfactory"
    if v >= Decimal("3.50"):
        return "Satisfactory"
    if v >= Decimal("3.00"):
        return "Needs Improvement"
    return "Poor"


def school_years():
    ys = [r["school_year"] for r in db.query("SELECT DISTINCT school_year FROM responses ORDER BY school_year DESC")]
    cur = get_setting("school_year", "").strip()
    if cur and cur not in ys:
        ys.insert(0, cur)
    return ys


def ratings_frame(school_year, semester=None):
    sql = ("SELECT r.id AS response_id, r.assignment_id, r.semester, r.section_id, rr.item_no, rr.rating "
           "FROM responses r JOIN response_ratings rr ON rr.response_id=r.id WHERE r.school_year=?")
    args = [school_year]
    if semester:
        sql += " AND r.semester=?"
        args.append(semester)
    return pd.DataFrame(db.query(sql, args),
                        columns=["response_id", "assignment_id", "semester", "section_id", "item_no", "rating"])


def summarize(df, method="category"):
    """Category averages, overall average and interpretation for one group of ratings."""
    if df is None or df.empty:
        return None
    d = df.copy()
    d["cat"] = d["item_no"].map(ITEM_CAT)
    cat = d.groupby("cat")["rating"].mean().to_dict()
    if method == "item":
        overall = float(d["rating"].mean())
    else:
        vals = [cat[c] for c in CAT_CODES if c in cat]
        overall = float(sum(vals) / len(vals))
    return {"n": int(d["response_id"].nunique()),
            "cats": {c: (float(cat[c]) if c in cat else None) for c in CAT_CODES},
            "overall": overall, "band": band(overall)}


def assignment_summary(school_year, semester=None, grade=None, teacher_id=None, method="category"):
    frame = ratings_frame(school_year, semester)
    rows = []
    for a in list_assignments():
        if grade and a["grade_level"] != grade:
            continue
        if teacher_id and a["teacher_id"] != teacher_id:
            continue
        s = summarize(frame[frame["assignment_id"] == a["id"]], method)
        if not s:
            continue
        row = {"assignment_id": a["id"], "Teacher": a["teacher_name"], "Grade": a["grade_level"],
               "Subject": a["label"], "Responses": s["n"]}
        for c in CAT_CODES:
            row[CAT_SHORT[c]] = fmt(s["cats"][c])
        row["Overall"] = fmt(s["overall"])
        row["Interpretation"] = s["band"]
        row["_overall"] = s["overall"]
        rows.append(row)
    return pd.DataFrame(rows)


def teacher_rollup(summary):
    """One line per teacher: average of that teacher's subject overall scores."""
    if summary is None or summary.empty:
        return pd.DataFrame()
    out = []
    for name, g in summary.groupby("Teacher", sort=True):
        avg = float(g["_overall"].mean())
        out.append({"Teacher": name, "Subjects evaluated": len(g), "Responses": int(g["Responses"].sum()),
                    "Overall (avg of subjects)": fmt(avg), "Interpretation": band(avg)})
    return pd.DataFrame(out)


def item_averages(df):
    if df is None or df.empty:
        return pd.DataFrame()
    means = df.groupby("item_no")["rating"].mean()
    rows = [{"No.": n, "Category": CAT_SHORT[ITEM_CAT[n]], "Statement": "The teacher " + ITEM_TEXT[n],
             "Average": fmt(float(means[n]))} for n in ITEM_NUMBERS if n in means.index]
    return pd.DataFrame(rows)


def comments_for(assignment_id, school_year, semester=None):
    sql = ("SELECT semester, section_name, submitted_date, comment_strategy, comment_management, comment_others "
           "FROM responses WHERE assignment_id=? AND school_year=?")
    args = [assignment_id, school_year]
    if semester:
        sql += " AND semester=?"
        args.append(semester)
    return db.query(sql + " ORDER BY submitted_date", args)


def section_counts(assignment_id, school_year, semester=None):
    sub = "SELECT COUNT(*) FROM responses r WHERE r.assignment_id=? AND r.section_id=s.id AND r.school_year=?"
    args = [assignment_id, school_year]
    if semester:
        sub += " AND r.semester=?"
        args.append(semester)
    rows = db.query(f"SELECT s.name AS section, s.enrolled AS enrolled, ({sub}) AS responses "
                    "FROM assignment_sections x JOIN sections s ON s.id=x.section_id "
                    "WHERE x.assignment_id=? ORDER BY s.name", args + [assignment_id])
    return rows


def assignment_progress(school_year, semester=None):
    sub = "SELECT COUNT(*) FROM responses r WHERE r.assignment_id=a.id AND r.school_year=?"
    args = [school_year]
    if semester:
        sub += " AND r.semester=?"
        args.append(semester)
    rows = db.query(
        "SELECT a.id, t.name AS teacher, a.grade_level, a.subject, a.component, a.active, "
        f"({sub}) AS responses, "
        "(SELECT COALESCE(SUM(s.enrolled),0) FROM assignment_sections x JOIN sections s ON s.id=x.section_id "
        "WHERE x.assignment_id=a.id) AS enrolled "
        "FROM assignments a JOIN teachers t ON t.id=a.teacher_id ORDER BY t.name, a.grade_level, a.subject",
        args)
    for r in rows:
        r["label"] = subject_label(r["subject"], r["component"])
    return rows


# =========================================================== BULK IMPORT
import io  # noqa: E402

_COL_ALIASES = {
    "teacher": "teacher", "teachername": "teacher", "nameofteacher": "teacher",
    "grade": "grade", "gradelevel": "grade", "level": "grade",
    "subject": "subject", "subjectname": "subject",
    "component": "component",
    "sections": "sections", "section": "sections",
    "sectionname": "section_name", "name": "section_name",
    "enrolled": "enrolled", "enrollment": "enrolled", "students": "enrolled",
    "numberofstudents": "enrolled", "enrolledstudents": "enrolled",
}


def _canon_columns(df):
    def canon(c):
        key = re.sub(r"[^a-z]", "", str(c).lower())
        return _COL_ALIASES.get(key, str(c))
    return df.rename(columns={c: canon(c) for c in df.columns})


def read_table(fileobj, filename):
    """Read an uploaded .csv or .xlsx into a DataFrame of strings."""
    name = (filename or "").lower()
    if name.endswith(".csv"):
        raw = fileobj.read()
        for enc in ("utf-8-sig", "cp1252"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    elif name.endswith((".xlsx", ".xlsm")):
        df = pd.read_excel(fileobj, dtype=str, keep_default_na=False)
    else:
        raise ValueError("Please upload a .csv or .xlsx file.")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def normalize_grade(value):
    m = re.search(r"(\d+)", str(value or ""))
    g = f"Grade {m.group(1)}" if m else ""
    return g if g in GRADE_LEVELS else None


def _split_names(text):
    return [p.strip() for p in re.split(r"[,;|\n]+", str(text or "")) if p.strip()]


def _clean(v):
    return " ".join(str(v or "").split())


# ---- sections & enrollment
def plan_section_import(df):
    """Returns (plan, error). plan: list of dicts with status add/update/skip/error."""
    df = _canon_columns(df)
    if "grade" not in df.columns or "section_name" not in df.columns and "sections" not in df.columns:
        return None, "The file needs the columns: Grade Level, Section, Enrolled."
    name_col = "section_name" if "section_name" in df.columns else "sections"
    existing = {(s["grade_level"], s["name"].lower()): s for s in list_sections()}
    plan, seen = [], set()
    for i, r in enumerate(df.to_dict("records"), start=2):
        if not any(_clean(v) for v in r.values()):
            continue
        grade, name = normalize_grade(r.get("grade")), _clean(r.get(name_col))
        raw_en = _clean(r.get("enrolled")) if "enrolled" in df.columns else ""
        row = {"row": i, "grade": grade or _clean(r.get("grade")), "section": name,
               "enrolled": raw_en, "status": "add", "note": ""}
        if not grade:
            row.update(status="error", note="Grade level must be Grade 11 or Grade 12.")
        elif not name:
            row.update(status="error", note="Section name is empty.")
        elif raw_en and not raw_en.isdigit():
            row.update(status="error", note="Enrolled must be a whole number.")
        elif (grade, name.lower()) in seen:
            row.update(status="error", note="Duplicate of an earlier row in this file.")
        else:
            seen.add((grade, name.lower()))
            ex = existing.get((grade, name.lower()))
            if ex:
                row["section_id"] = ex["id"]
                row["section"] = ex["name"]  # keep the stored spelling
                if raw_en and int(raw_en) != ex["enrolled"]:
                    row.update(status="update", note=f"Enrollment {ex['enrolled']} -> {raw_en}")
                else:
                    row.update(status="skip", note="Already exists.")
        plan.append(row)
    return plan, None


def apply_section_import(plan):
    done = {"add": 0, "update": 0}
    for p in plan:
        if p["status"] == "add":
            ok, _ = add_section(p["grade"], p["section"], int(p["enrolled"] or 0))
            done["add"] += 1 if ok else 0
        elif p["status"] == "update":
            update_section(p["section_id"], p["section"], int(p["enrolled"]))
            done["update"] += 1
    return done


# ---- teachers (names only)
def add_teachers_bulk(text):
    """One name per line. Returns (added, already_existing)."""
    existing = {t["name"].lower() for t in list_teachers()}
    added, dup = [], []
    for name in [_clean(x) for x in re.split(r"[\n;]+", text or "")]:
        if not name:
            continue
        if name.lower() in existing:
            dup.append(name)
            continue
        ok, _ = add_teacher(name)
        (added if ok else dup).append(name)
        existing.add(name.lower())
    return added, dup


# ---- teachers + subjects + sections
def plan_assignment_import(df, create_sections=True):
    """Dry run of a teacher/subject import. Returns (plan, error)."""
    df = _canon_columns(df)
    missing = [c for c in ("teacher", "grade", "subject", "sections") if c not in df.columns]
    if missing:
        return None, ("Missing column(s): " + ", ".join(missing) +
                      ". Required columns: Teacher, Grade Level, Subject, Sections (Component is optional).")
    teachers = {t["name"].lower(): t for t in list_teachers()}
    sec_by_grade = {g: {s["name"].lower(): s for s in list_sections(g)} for g in GRADE_LEVELS}
    existing = {(a["teacher_id"], a["grade_level"], a["subject"].lower(), a["component"].lower()): a
                for a in list_assignments()}
    plan, seen = [], set()
    for i, r in enumerate(df.to_dict("records"), start=2):
        if not any(_clean(v) for v in r.values()):
            continue
        teacher = _clean(r.get("teacher"))
        grade = normalize_grade(r.get("grade"))
        subject = _clean(r.get("subject"))
        component = _clean(r.get("component")) if "component" in df.columns else ""
        if not component and ":" in subject:
            subject, component = [p.strip() for p in subject.split(":", 1)]
        names = _split_names(r.get("sections"))
        row = {"row": i, "teacher": teacher, "grade": grade or _clean(r.get("grade")), "subject": subject,
               "component": component, "sections": [], "new_sections": [], "status": "add", "note": ""}
        err = None
        if not teacher:
            err = "Teacher name is empty."
        elif not grade:
            err = "Grade level must be Grade 11 or Grade 12."
        elif not subject:
            err = "Subject is empty."
        elif not names:
            err = "No sections listed."
        if not err:
            known = sec_by_grade[grade]
            for n in names:
                hit = known.get(n.lower())
                if hit:
                    row["sections"].append(hit["name"])
                elif create_sections:
                    row["sections"].append(n)
                    row["new_sections"].append(n)
                else:
                    err = f"Section \u201c{n}\u201d does not exist for {grade}."
                    break
        if err:
            row.update(status="error", note=err)
        else:
            key = (teacher.lower(), grade, subject.lower(), component.lower())
            t = teachers.get(teacher.lower())
            if key in seen:
                row.update(status="error", note="Duplicate of an earlier row in this file.")
            else:
                seen.add(key)
                notes = []
                if not t:
                    notes.append("new teacher")
                if row["new_sections"]:
                    notes.append("new section(s): " + ", ".join(row["new_sections"]))
                ex = existing.get((t["id"], grade, subject.lower(), component.lower())) if t else None
                if ex:
                    have = {s["name"].lower() for s in ex["sections"]}
                    extra = [s for s in row["sections"] if s.lower() not in have]
                    if extra:
                        row.update(status="merge")
                        notes.append("adds section(s) to existing assignment: " + ", ".join(extra))
                    else:
                        row.update(status="skip")
                        notes.append("already exists")
                row["note"] = "; ".join(notes)
        plan.append(row)
    return plan, None


def apply_assignment_import(plan):
    """Apply the add/merge rows of a plan. Returns a summary dict."""
    out = {"teachers": 0, "sections": 0, "added": 0, "merged": 0, "failed": []}
    teachers = {t["name"].lower(): t["id"] for t in list_teachers()}
    for p in plan:
        if p["status"] not in ("add", "merge"):
            continue
        try:
            tid = teachers.get(p["teacher"].lower())
            if tid is None:
                ok, msg = add_teacher(p["teacher"])
                if not ok:
                    raise ValueError(msg)
                tid = next(t["id"] for t in list_teachers() if t["name"].lower() == p["teacher"].lower())
                teachers[p["teacher"].lower()] = tid
                out["teachers"] += 1
            have = {s["name"].lower(): s["id"] for s in list_sections(p["grade"])}
            ids = []
            for n in p["sections"]:
                if n.lower() not in have:
                    ok, msg = add_section(p["grade"], n, 0)
                    if not ok:
                        raise ValueError(msg)
                    have = {s["name"].lower(): s["id"] for s in list_sections(p["grade"])}
                    out["sections"] += 1
                ids.append(have[n.lower()])
            if p["status"] == "add":
                ok, res = create_assignment(tid, p["grade"], p["subject"], p["component"], ids)
                if not ok:
                    raise ValueError(res)
                out["added"] += 1
            else:
                row = db.query("SELECT id FROM assignments WHERE teacher_id=? AND grade_level=? AND subject=? "
                               "AND component=?", (tid, p["grade"], p["subject"], p["component"]))
                if not row:
                    # subject/component differ only in letter case from the stored one
                    row = [a for a in list_assignments() if a["teacher_id"] == tid and a["grade_level"] == p["grade"]
                           and a["subject"].lower() == p["subject"].lower()
                           and a["component"].lower() == p["component"].lower()]
                db.batch([("INSERT OR IGNORE INTO assignment_sections(assignment_id,section_id) VALUES(?,?)",
                           (row[0]["id"], sid)) for sid in ids])
                out["merged"] += 1
        except Exception as e:  # noqa: BLE001
            out["failed"].append(f"Row {p['row']}: {e}")
    return out


def assignment_template_df():
    return pd.DataFrame([
        {"Teacher": "Ms. Maria Reyes", "Grade Level": "Grade 11", "Subject": "Physics", "Component": "",
         "Sections": "11-STEM A, 11-STEM B"},
        {"Teacher": "Ms. Maria Reyes", "Grade Level": "Grade 11", "Subject": "Biology", "Component": "",
         "Sections": "11-STEM B"},
        {"Teacher": "Mr. Juan Santos", "Grade Level": "Grade 11", "Subject": "Life and Career Skills",
         "Component": "Physical Education", "Sections": "11-STEM A, 11-STEM B"},
        {"Teacher": "Mrs. Ana Cruz", "Grade Level": "Grade 11", "Subject": "Life and Career Skills",
         "Component": "Personal Development", "Sections": "11-STEM A, 11-STEM B"},
    ])


def section_template_df():
    return pd.DataFrame([
        {"Grade Level": "Grade 11", "Section": "11-STEM A", "Enrolled": "40"},
        {"Grade Level": "Grade 11", "Section": "11-STEM B", "Enrolled": "38"},
        {"Grade Level": "Grade 12", "Section": "12-HUMSS A", "Enrolled": "35"},
    ])
