import streamlit as st
from tpas_db import init_db, using_turso

st.set_page_config(page_title="DBES TPAS", page_icon="📋")
init_db()

st.title("DBES TPAS")
st.caption("Teacher Performance Appraisal System")

st.page_link("pages/1_Student_Evaluation.py", label="Student Evaluation of Teachers (Form 6)", icon="📝")
st.page_link("pages/2_Form6_Questions.py", label="Manage Form 6 Questions (admin)", icon="⚙️")
st.page_link("pages/3_Results.py", label="Results (admin)", icon="📊")

if not using_turso():
    st.sidebar.warning("Using local SQLite (testing). Add Turso secrets to save permanently.")
