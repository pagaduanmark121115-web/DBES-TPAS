import pandas as pd
import streamlit as st

import auth
import core
import ui
from tpas_form import COMMENT_FIELDS, GRADE_LEVELS, SEMESTERS

auth.require_login()
ui.show_flash()
st.title("📈 Results")

years = core.school_years()
if not years:
    st.info("No school year or responses yet.")
    st.stop()

f1, f2, f3, f4 = st.columns(4)
sy = f1.selectbox("School year", years)
sem_choice = f2.selectbox("Semester", ["All semesters"] + SEMESTERS)
grade = f3.selectbox("Grade level", ["All"] + GRADE_LEVELS)
teachers = core.list_teachers()
tch = f4.selectbox("Teacher", [None] + teachers, format_func=lambda t: "All" if t is None else t["name"])

semester = None if sem_choice == "All semesters" else sem_choice
method = core.get_setting("overall_method", "category")
summary = core.assignment_summary(sy, semester, None if grade == "All" else grade,
                                  tch["id"] if tch else None, method)
if summary.empty:
    st.info("No responses match these filters yet.")
    st.stop()

show_cols = [c for c in summary.columns if c not in ("assignment_id", "_overall")]
st.subheader("Per teacher and subject")
st.dataframe(summary[show_cols], hide_index=True)
st.download_button("Download this table (CSV)", summary[show_cols].to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"tpas_results_{sy}.csv", mime="text/csv")

st.subheader("Per teacher (all subjects combined)")
roll = core.teacher_rollup(summary)
st.dataframe(roll, hide_index=True)
st.caption("Overall score = " + ("average of the four category averages" if method == "category"
                                 else "average of all 28 statement ratings")
           + ". Bands: 4.50-5.00 Outstanding, 4.00-4.49 Very Satisfactory, 3.50-3.99 Satisfactory, "
             "3.00-3.49 Needs Improvement, 2.99 and below Poor. A teacher's combined score is the average of "
             "their subjects' overall scores.")

st.subheader("Details")
pick = st.selectbox("Teacher and subject", summary.to_dict("records"),
                    format_func=lambda r: f"{r['Teacher']} | {r['Grade']} | {r['Subject']} ({r['Responses']} responses)")
aid = int(pick["assignment_id"])
frame = core.ratings_frame(sy, semester)
frame = frame[frame["assignment_id"] == aid]
s = core.summarize(frame, method)

m1, m2, m3 = st.columns(3)
m1.metric("Responses", s["n"])
m2.metric("Overall average", core.fmt(s["overall"]))
m3.metric("Interpretation", s["band"])

tab_i, tab_c, tab_s = st.tabs(["Statement averages", "Comments", "Responses by section"])
with tab_i:
    st.dataframe(core.item_averages(frame), hide_index=True)
with tab_c:
    rows = core.comments_for(aid, sy, semester)
    any_comment = False
    for col, label in COMMENT_FIELDS:
        texts = [(r["section_name"], r["semester"], r[col]) for r in rows if (r[col] or "").strip()]
        st.markdown(f"**{label}** ({len(texts)})")
        for section, sem, text in texts:
            any_comment = True
            st.markdown(f"- {text}  \n  <span style='color:gray;font-size:0.8em'>{section} | {sem}</span>",
                        unsafe_allow_html=True)
        if not texts:
            st.caption("No comments.")
    if not any_comment:
        st.caption("Students left no comments for this selection.")
with tab_s:
    counts = core.section_counts(aid, sy, semester)
    tbl = []
    for c in counts:
        rate = f"{100 * c['responses'] / c['enrolled']:.0f}%" if c["enrolled"] else "-"
        tbl.append({"Section": c["section"], "Enrolled": c["enrolled"], "Evaluated": c["responses"],
                    "Response rate": rate if semester else "(pick a semester)"})
    st.dataframe(pd.DataFrame(tbl), hide_index=True)
    st.caption("Each student can evaluate a teacher and subject once per semester (checked by email). "
               "Answers are not linked to emails.")
