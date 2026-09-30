"""Run:  python tests/test_core.py   (uses a temporary local SQLite database)"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TPAS_LOCAL_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")

import db, core
from tpas_form import ITEM_NUMBERS

db.init()

# bands (boundaries)
cases = {5: "Outstanding", 4.50: "Outstanding", 4.499: "Outstanding", 4.494: "Very Satisfactory",
         4.0: "Very Satisfactory", 3.995: "Very Satisfactory", 3.99: "Satisfactory", 3.5: "Satisfactory",
         3.49: "Needs Improvement", 3.0: "Needs Improvement", 2.995: "Needs Improvement", 2.99: "Poor", 1: "Poor"}
for v, exp in cases.items():
    assert core.band(v) == exp, (v, core.band(v), exp)

# users
assert not core.any_user()
assert core.create_user("hradmin", "password1")[0]
assert core.verify_user("hradmin", "password1") and not core.verify_user("hradmin", "wrong")

# setup
core.set_setting("school_year", "2026-2027")
assert core.add_section("Grade 11", "11-STEM A", 40)[0]
assert core.add_section("Grade 11", "11-STEM B", 38)[0]
assert not core.add_section("Grade 11", "11-STEM A", 40)[0]
secs = core.list_sections("Grade 11")
sids = [s["id"] for s in secs]
assert core.add_teacher("Ms. Reyes")[0] and not core.add_teacher("Ms. Reyes")[0]
tid = core.list_teachers()[0]["id"]
ok, tok1 = core.create_assignment(tid, "Grade 11", "Life and Career Skills", "Physical Education", sids)
ok2, tok2 = core.create_assignment(tid, "Grade 11", "Physics", "", sids[:1])
assert ok and ok2 and tok1 != tok2 and len(tok1) == 8
assert not core.create_assignment(tid, "Grade 11", "Physics", "", sids)[0]  # duplicate
a = core.get_assignment_by_token(tok1.lower())
assert a["label"] == "Life and Career Skills: Physical Education"
assert core.build_link(tok1).endswith("/evaluate?t=" + tok1)

def ratings(v):
    return {n: v for n in ITEM_NUMBERS}

# submit
ok, msg = core.submit_response(tok1, "1st Semester", sids[0], "Stu1@School.edu", ratings(5), {"comment_strategy": "Very clear lessons"})
assert ok, msg
ok, msg = core.submit_response(tok1, "1st Semester", sids[0], "stu1@school.edu", ratings(5), {})
assert not ok and "already" in msg          # duplicate (case-insensitive email)
assert core.submit_response(tok1, "2nd Semester", sids[0], "stu1@school.edu", ratings(3), {})[0]  # other semester ok
assert core.submit_response(tok1, "1st Semester", sids[1], "stu2@school.edu", ratings(4), {"comment_others": "aaaa"})[0] is False
assert core.submit_response(tok1, "1st Semester", sids[1], "stu2@school.edu", ratings(4), {})[0]
bad = ratings(4); del bad[7]
assert "Unanswered: 7" in core.submit_response(tok1, "1st Semester", sids[1], "stu3@school.edu", bad, {})[1]
assert not core.submit_response(tok1, "1st Semester", sids[1], "not-an-email", ratings(4), {})[0]
assert not core.submit_response(tok2, "1st Semester", sids[1], "stu3@school.edu", ratings(4), {})[0]  # section not in Physics
assert not core.submit_response("ZZZZZZZZ", "1st Semester", sids[1], "stu3@school.edu", ratings(4), {})[0]

# domain restriction
core.set_setting("allowed_domains", "school.edu")
assert not core.submit_response(tok1, "1st Semester", sids[1], "x@gmail.com", ratings(4), {})[0]
assert core.submit_response(tok1, "1st Semester", sids[1], "x@mail.school.edu", ratings(4), {})[0]
core.set_setting("allowed_domains", "")

# closed
core.set_setting("evaluation_open", "0")
assert not core.submit_response(tok1, "1st Semester", sids[1], "late@school.edu", ratings(4), {})[0]
core.set_setting("evaluation_open", "1")

# anonymity: no email or hash in responses; respondents holds only a hash
cols = [r["name"] for r in db.query("PRAGMA table_info(responses)")]
assert not any("email" in c for c in cols)
assert db.query("SELECT COUNT(*) AS n FROM respondents")[0]["n"] == db.query("SELECT COUNT(*) AS n FROM responses")[0]["n"]
assert "@" not in str(db.query("SELECT * FROM respondents"))

# scoring: sem1 = 5 (sec A), 4 (sec B), 4 (sec B, domain test) -> mean 4.333
s = core.assignment_summary("2026-2027", "1st Semester")
row = s[s["assignment_id"] == a["id"]].iloc[0]
assert row["Responses"] == 3 and row["Overall"] == "4.33" and row["Interpretation"] == "Very Satisfactory", row
s_all = core.assignment_summary("2026-2027", None)
assert s_all.iloc[0]["Responses"] == 4
assert list(core.teacher_rollup(s_all)["Teacher"]) == ["Ms. Reyes"]

# unequal category sizes: category vs item weighting
import pandas as pd
rows = [{"response_id": "r", "assignment_id": 1, "semester": "x", "section_id": 1, "item_no": n,
         "rating": 5 if n <= 6 else 1} for n in ITEM_NUMBERS]
df = pd.DataFrame(rows)
c = core.summarize(df, "category"); i = core.summarize(df, "item")
assert round(c["cats"]["A"], 2) == 5 and round(c["overall"], 2) == 2.0
assert round(i["overall"], 4) == round((6 * 5 + 22) / 28, 4)

# section counts vs enrolled
sc = core.section_counts(a["id"], "2026-2027", "1st Semester")
assert {r["section"]: r["responses"] for r in sc} == {"11-STEM A": 1, "11-STEM B": 2}, sc
assert core.assignment_progress("2026-2027")[0]["enrolled"] in (78, 40)

# item averages + comments
assert len(core.item_averages(core.ratings_frame("2026-2027"))) == 28
assert any(c["comment_strategy"] for c in core.comments_for(a["id"], "2026-2027"))

# delete rules
assert not core.delete_assignment(a["id"])[0]
assert core.delete_assignment(core.get_assignment_by_token(tok2)["id"])[0]
assert not core.delete_section(sids[0])[0]
print("ALL CORE TESTS PASSED")
