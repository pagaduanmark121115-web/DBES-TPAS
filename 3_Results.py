import pandas as pd
import streamlit as st
from tpas_db import init_db, require_admin, run

st.set_page_config(page_title="TPAS Results", page_icon="📊", layout="wide")
init_db()
require_admin()

st.title("TPAS Results")

sys_ = [r["sy"] for r in run("SELECT DISTINCT sy FROM tpas_evaluations ORDER BY sy DESC")]
if not sys_:
    st.info("No evaluations submitted yet.")
    st.stop()

sy = st.selectbox("School Year", sys_)

st.subheader("Overall average per teacher")
overall = run(
    """SELECT e.teacher_name AS Teacher, e.school AS School,
              COUNT(DISTINCT e.id) AS Evaluators,
              ROUND(AVG(a.rating), 2) AS Average
       FROM tpas_evaluations e JOIN tpas_answers a ON a.evaluation_id = e.id
       WHERE e.sy = ?
       GROUP BY e.teacher_name, e.school
       ORDER BY Average DESC""",
    (sy,),
)
st.dataframe(pd.DataFrame(overall), hide_index=True, use_container_width=True)

st.subheader("Average per section")
by_section = run(
    """SELECT e.teacher_name AS Teacher, q.section AS Section, ROUND(AVG(a.rating), 2) AS Average
       FROM tpas_evaluations e
       JOIN tpas_answers a ON a.evaluation_id = e.id
       JOIN tpas_questions q ON q.id = a.question_id
       WHERE e.sy = ?
       GROUP BY e.teacher_name, q.section""",
    (sy,),
)
if by_section:
    pivot = pd.DataFrame(by_section).pivot(index="Teacher", columns="Section", values="Average")
    st.dataframe(pivot, use_container_width=True)

st.subheader("Comments and suggestions")
teachers = [r["Teacher"] for r in overall]
chosen = st.selectbox("Teacher", teachers)
comments = run(
    """SELECT comment_strategy, comment_classroom, comment_others, submitted_at
       FROM tpas_evaluations WHERE sy = ? AND teacher_name = ? ORDER BY submitted_at DESC""",
    (sy, chosen),
)
for c in comments:
    if any([c["comment_strategy"], c["comment_classroom"], c["comment_others"]]):
        with st.container(border=True):
            st.caption(c["submitted_at"])
            if c["comment_strategy"]:
                st.markdown(f"**Teaching Strategy:** {c['comment_strategy']}")
            if c["comment_classroom"]:
                st.markdown(f"**Classroom Management:** {c['comment_classroom']}")
            if c["comment_others"]:
                st.markdown(f"**Others:** {c['comment_others']}")
