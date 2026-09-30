import pandas as pd
import streamlit as st

import auth
import core
import ui

auth.require_login()
ui.show_flash()
st.title("📊 Dashboard")
ui.dev_mode_banner()
ui.base_url_warning()

sy = core.get_setting("school_year", "").strip()
is_open = core.get_setting("evaluation_open", "1") == "1"
if not sy:
    st.warning("The school year is not set yet. Go to Settings first.")

teachers = core.list_teachers(active_only=True)
progress = core.assignment_progress(sy) if sy else []
c1, c2, c3, c4 = st.columns(4)
c1.metric("School year", sy or "Not set")
c2.metric("Active teachers", len(teachers))
c3.metric("Active assignments", sum(1 for p in progress if p["active"]))
c4.metric("Responses this school year", sum(p["responses"] for p in progress))
st.write("Evaluation status: " + ("🟢 **Open**" if is_open else "🔴 **Closed** (students cannot submit)"))

st.subheader("Responses per teacher and subject")
if progress:
    df = pd.DataFrame([{"Teacher": p["teacher"], "Grade": p["grade_level"], "Subject": p["label"],
                        "Active": "Yes" if p["active"] else "No", "Responses": p["responses"],
                        "Students enrolled (all sections)": p["enrolled"]} for p in progress])
    st.dataframe(df, hide_index=True)
    st.caption("Students enrolled = total enrollment of the sections that take this subject. "
               "See Results for the response rate by section and semester.")
else:
    st.info("No assignments yet. Add sections, then teachers and their assignments.")
