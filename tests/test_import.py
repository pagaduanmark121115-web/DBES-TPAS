"""Run:  python tests/test_import.py"""
import io, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TPAS_LOCAL_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
import pandas as pd
import db, core

db.init()

# ---- sections import from CSV (with BOM, odd header case)
csv = "\ufeffgrade level,SECTION,Enrolled\nGrade 11,11-STEM A,40\n11,11-STEM B,38\nGrade 12,12-HUMSS A,35\nGrade 9,X,1\nGrade 11,11-STEM A,40\nGrade 11,Bad,abc\n"
df = core.read_table(io.BytesIO(csv.encode("utf-8")), "sections.csv")
plan, err = core.plan_section_import(df)
assert err is None
st = [p["status"] for p in plan]
assert st == ["add", "add", "add", "error", "error", "error"], st
assert core.apply_section_import(plan) == {"add": 3, "update": 0}
plan, _ = core.plan_section_import(df)
assert [p["status"] for p in plan][:3] == ["skip", "skip", "skip"]
df2 = pd.DataFrame({"Grade Level": ["Grade 11"], "Section": ["11-stem a"], "Enrolled": ["42"]})
plan, _ = core.plan_section_import(df2)
assert plan[0]["status"] == "update"
assert core.apply_section_import(plan)["update"] == 1
assert [s["enrolled"] for s in core.list_sections("Grade 11") if s["name"] == "11-STEM A"] == [42]

# ---- teacher names
added, dup = core.add_teachers_bulk("Ms. Maria Reyes\n  mr.  juan santos \nMs. Maria Reyes\n\n")
assert added == ["Ms. Maria Reyes", "mr. juan santos"] and dup == ["Ms. Maria Reyes"], (added, dup)

# ---- teachers + subjects
tpl = core.assignment_template_df()
plan, err = core.plan_assignment_import(tpl, create_sections=False)
assert err is None
assert [p["status"] for p in plan] == ["add", "add", "add", "add"], [(p["status"], p["note"]) for p in plan]
assert plan[2]["component"] == "Physical Education"
res = core.apply_assignment_import(plan)
assert res["added"] == 4 and res["teachers"] == 1 and not res["failed"], res  # only Mrs. Ana Cruz is new
asg = core.list_assignments()
assert len(asg) == 4
lcs = [a for a in asg if a["subject"] == "Life and Career Skills"]
assert {a["component"] for a in lcs} == {"Physical Education", "Personal Development"}
assert len({a["token"] for a in asg}) == 4

# re-import: everything skipped; new section -> merge
plan, _ = core.plan_assignment_import(tpl, create_sections=False)
assert all(p["status"] == "skip" for p in plan)
more = pd.DataFrame([{"teacher": "ms. maria reyes", "GRADE": "11", "Subject": "Biology", "Sections": "11-STEM A; 11-STEM B"},
                     {"teacher": "Ms. Maria Reyes", "GRADE": "12", "Subject": "Life and Career Skills: Religious Education", "Sections": "12-HUMSS A, 12-NEW"},
                     {"teacher": "", "GRADE": "11", "Subject": "Math", "Sections": "11-STEM A"},
                     {"teacher": "Ms. Maria Reyes", "GRADE": "11", "Subject": "Math", "Sections": "Nope"}])
plan, err = core.plan_assignment_import(more, create_sections=False)
assert [p["status"] for p in plan] == ["merge", "error", "error", "error"], [(p["status"], p["note"]) for p in plan]
plan, _ = core.plan_assignment_import(more, create_sections=True)
assert [p["status"] for p in plan] == ["merge", "add", "error", "add"], [(p["status"], p["note"]) for p in plan]
assert plan[1]["subject"] == "Life and Career Skills" and plan[1]["component"] == "Religious Education"
res = core.apply_assignment_import(plan)
assert res["merged"] == 1 and res["added"] == 2 and res["sections"] == 2 and not res["failed"], res
bio = [a for a in core.list_assignments() if a["subject"] == "Biology" and a["grade_level"] == "Grade 11"][0]
assert {s["name"] for s in bio["sections"]} == {"11-STEM A", "11-STEM B"}

# missing columns
plan, err = core.plan_assignment_import(pd.DataFrame({"Teacher": ["x"]}))
assert plan is None and "Missing" in err

# xlsx round trip
buf = io.BytesIO(); core.assignment_template_df().to_excel(buf, index=False); buf.seek(0)
d = core.read_table(buf, "t.xlsx")
assert list(d.columns) == ["Teacher", "Grade Level", "Subject", "Component", "Sections"] and len(d) == 4
print("ALL IMPORT TESTS PASSED")
