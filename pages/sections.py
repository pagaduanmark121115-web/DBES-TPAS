import pandas as pd
import streamlit as st

import auth
import core
import ui
from tpas_form import GRADE_LEVELS

auth.require_login()
ui.show_flash()
st.title("🏫 Sections & Enrollment")
st.caption("Enrollment is used to show how many students of each section have already evaluated a teacher.")

with st.form("add_section", clear_on_submit=True):
    c1, c2, c3 = st.columns([1, 2, 1])
    grade = c1.selectbox("Grade level", GRADE_LEVELS)
    name = c2.text_input("Section name", placeholder="e.g. 11-STEM A")
    enrolled = c3.number_input("Enrolled students", min_value=0, step=1, value=0)
    if st.form_submit_button("Add section", type="primary"):
        ok, msg = core.add_section(grade, name, enrolled)
        if ok:
            ui.flash(msg)
            st.rerun()
        else:
            st.error(msg)

secs = core.list_sections()
if not secs:
    st.info("No sections yet.")
    st.stop()

st.subheader("Edit enrollment")
df = pd.DataFrame(secs)[["id", "grade_level", "name", "enrolled"]]
edited = st.data_editor(
    df, key="sec_editor", hide_index=True, disabled=["id", "grade_level"],
    column_config={"id": None, "grade_level": "Grade level", "name": "Section",
                   "enrolled": st.column_config.NumberColumn("Enrolled students", min_value=0, step=1)})
if st.button("Save changes"):
    changed = 0
    for old, new in zip(df.to_dict("records"), edited.to_dict("records")):
        if old["name"] != new["name"] or int(old["enrolled"]) != int(new["enrolled"]):
            if not str(new["name"]).strip():
                st.error("Section name cannot be empty.")
                st.stop()
            core.update_section(int(old["id"]), new["name"], new["enrolled"])
            changed += 1
    ui.flash(f"Saved {changed} change(s).")
    st.rerun()

with st.expander("Delete a section"):
    pick = st.selectbox("Section", secs, format_func=lambda s: f"{s['grade_level']} - {s['name']}", key="del_sec")
    if st.button("Delete section"):
        ok, msg = core.delete_section(pick["id"])
        if ok:
            ui.flash(msg)
            st.rerun()
        else:
            st.error(msg)
