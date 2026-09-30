import pandas as pd
import streamlit as st

import auth
import core
import ui
from tpas_form import GRADE_LEVELS

auth.require_login()
ui.show_flash()
st.title("👩‍🏫 Teachers & Assignments")
st.caption("Each assignment is one teacher + grade level + subject, and gets its own link and QR code. "
           "For a subject shared by several teachers (e.g. Life and Career Skills), give each teacher their "
           "own assignment and fill in the Component.")

tab_t, tab_a = st.tabs(["Teachers", "Assignments"])

# ------------------------------------------------------------------ teachers
with tab_t:
    with st.form("add_teacher", clear_on_submit=True):
        name = st.text_input("Teacher name", placeholder="e.g. Ms. Maria Reyes")
        if st.form_submit_button("Add teacher", type="primary"):
            ok, msg = core.add_teacher(name)
            if ok:
                ui.flash(msg)
                st.rerun()
            else:
                st.error(msg)
    teachers = core.list_teachers()
    if teachers:
        st.dataframe(pd.DataFrame([{"Teacher": t["name"], "Status": "Active" if t["active"] else "Inactive"}
                                   for t in teachers]), hide_index=True)
        with st.expander("Rename or deactivate a teacher"):
            t = st.selectbox("Teacher", teachers, format_func=lambda x: x["name"], key="edit_teacher")
            new_name = st.text_input("Name", value=t["name"], key=f"rn_{t['id']}")
            active = st.checkbox("Active (inactive teachers' links stop working)", value=bool(t["active"]),
                                 key=f"ac_{t['id']}")
            if st.button("Save teacher"):
                ok, msg = core.rename_teacher(t["id"], new_name)
                if ok:
                    core.set_teacher_active(t["id"], active)
                    ui.flash("Teacher updated.")
                    st.rerun()
                else:
                    st.error(msg)
    else:
        st.info("No teachers yet.")

# --------------------------------------------------------------- assignments
with tab_a:
    active_teachers = core.list_teachers(active_only=True)
    st.subheader("Add an assignment")
    if not active_teachers:
        st.info("Add a teacher first.")
    else:
        c1, c2 = st.columns(2)
        teacher = c1.selectbox("Teacher", active_teachers, format_func=lambda x: x["name"], key="new_teacher")
        grade = c2.selectbox("Grade level", GRADE_LEVELS, key="new_grade")
        c3, c4 = st.columns(2)
        subject = c3.text_input("Subject", key="new_subject", placeholder="e.g. Physics")
        component = c4.text_input("Component (optional)", key="new_component",
                                  placeholder="e.g. Physical Education (for Life and Career Skills)")
        grade_secs = core.list_sections(grade)
        picked = st.multiselect("Sections taking this subject", grade_secs, format_func=lambda s: s["name"],
                                key=f"new_secs_{grade}")
        if not grade_secs:
            st.caption("No sections for this grade level yet. Add them under Sections & Enrollment.")
        if st.button("Add assignment", type="primary"):
            ok, res = core.create_assignment(teacher["id"], grade, subject, component, [s["id"] for s in picked])
            if ok:
                ui.flash(f"Assignment added. Link: {core.build_link(res)}")
                st.rerun()
            else:
                st.error(res)

    st.subheader("All assignments")
    assignments = core.list_assignments()
    if not assignments:
        st.info("No assignments yet.")
    else:
        st.dataframe(pd.DataFrame([{
            "Teacher": a["teacher_name"], "Grade": a["grade_level"], "Subject": a["label"],
            "Sections": ", ".join(s["name"] for s in a["sections"]),
            "Status": "Active" if a["active"] else "Inactive", "Responses": a["n_responses"],
            "Code": a["token"]} for a in assignments]), hide_index=True)

        with st.expander("Edit, deactivate or delete an assignment"):
            a = st.selectbox("Assignment", assignments, key="edit_assign",
                             format_func=lambda x: f"{x['teacher_name']} | {x['grade_level']} | {x['label']}")
            k = a["id"]
            st.caption(f"The link/QR code for this assignment ({a['token']}) never changes when you edit it.")
            e1, e2 = st.columns(2)
            subj = e1.text_input("Subject", value=a["subject"], key=f"es_{k}")
            comp = e2.text_input("Component", value=a["component"], key=f"ec_{k}")
            gsecs = core.list_sections(a["grade_level"])
            current = [s for s in gsecs if s["id"] in {x["id"] for x in a["sections"]}]
            new_secs = st.multiselect("Sections", gsecs, default=current, format_func=lambda s: s["name"],
                                      key=f"esec_{k}")
            act = st.checkbox("Active", value=bool(a["active"]), key=f"eact_{k}")
            b1, b2 = st.columns(2)
            if b1.button("Save changes", key=f"save_{k}"):
                ok, msg = core.update_assignment(k, subj, comp, [s["id"] for s in new_secs], act)
                if ok:
                    ui.flash(msg)
                    st.rerun()
                else:
                    st.error(msg)
            if b2.button("Delete assignment", key=f"del_{k}"):
                ok, msg = core.delete_assignment(k)
                if ok:
                    ui.flash(msg)
                    st.rerun()
                else:
                    st.error(msg)
