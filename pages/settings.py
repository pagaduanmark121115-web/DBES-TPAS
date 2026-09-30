import streamlit as st

import auth
import core
import db
import ui

auth.require_login()
ui.show_flash()
st.title("⚙️ Settings")
ui.dev_mode_banner()
ui.base_url_warning()

st.subheader("Evaluation period")
with st.form("period"):
    sy = st.text_input("School year", value=core.get_setting("school_year", ""), placeholder="e.g. 2026-2027",
                       help="Shown on the form and saved with every response.")
    is_open = st.toggle("Evaluation open (students can submit)", value=core.get_setting("evaluation_open", "1") == "1")
    domains = st.text_input("Allowed student email domain(s)", value=core.get_setting("allowed_domains", ""),
                            placeholder="e.g. dbes.edu.ph  (separate several with commas; leave blank to allow any email)")
    method = st.radio(
        "How is the overall average computed?", ["category", "item"],
        index=0 if core.get_setting("overall_method", "category") == "category" else 1,
        format_func=lambda m: "Average of the 4 category averages" if m == "category"
        else "Average of all 28 statement ratings")
    if st.form_submit_button("Save settings", type="primary"):
        if not sy.strip():
            st.error("School year is required.")
        else:
            core.set_setting("school_year", sy.strip())
            core.set_setting("evaluation_open", "1" if is_open else "0")
            core.set_setting("allowed_domains", domains.strip())
            core.set_setting("overall_method", method)
            ui.flash("Settings saved.")
            st.rerun()

st.subheader("Change my password")
with st.form("pw"):
    p1 = st.text_input("New password (at least 8 characters)", type="password")
    p2 = st.text_input("Confirm new password", type="password")
    if st.form_submit_button("Update password"):
        if p1 != p2:
            st.error("Passwords do not match.")
        else:
            ok, msg = core.change_password(auth.current_user(), p1)
            (st.success if ok else st.error)(msg)

st.subheader("System")
st.write(f"Database: **{db.backend_name()}**")
st.write(f"Link base address: `{core.base_url()}`")
