import streamlit as st

st.set_page_config(page_title="DBES Teacher Performance Appraisal", page_icon="🎓", layout="wide")

import auth
import core
import db
import ui

try:
    db.init()
except Exception as e:  # noqa: BLE001
    st.error(f"Could not connect to the database: {e}")
    st.info("If you use Turso, check TURSO_DATABASE_URL (use the https:// form) and TURSO_AUTH_TOKEN in the app secrets.")
    st.stop()


def gate():
    st.title("🎓 DBES Teacher Performance Appraisal System")
    ui.dev_mode_banner()
    st.caption("HR access only. Students: please scan the QR code or open the link given to you.")
    if not core.any_user():
        auth.first_run_form()
    else:
        auth.login_form()


gate_page = st.Page(gate, title="HR Login", icon="🔒", url_path="login", default=True)
evaluate_page = st.Page("pages/evaluate.py", title="Evaluation Form", icon="📝", url_path="evaluate")

user = auth.current_user()
if user:
    nav = st.navigation({
        "Overview": [st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True)],
        "Setup": [
            st.Page("pages/bulk_import.py", title="Bulk Import", icon="📥", url_path="bulk-import"),
            st.Page("pages/sections.py", title="Sections & Enrollment", icon="🏫", url_path="sections"),
            st.Page("pages/teachers.py", title="Teachers & Assignments", icon="👩‍🏫", url_path="teachers"),
            st.Page("pages/qr_links.py", title="QR Codes & Links", icon="🔗", url_path="qr-links"),
        ],
        "Reports": [st.Page("pages/results.py", title="Results", icon="📈", url_path="results")],
        "System": [st.Page("pages/settings.py", title="Settings", icon="⚙️", url_path="settings"), evaluate_page],
    })
    with st.sidebar:
        st.caption(f"Logged in as **{user}**")
        if st.button("Log out"):
            auth.logout()
else:
    # Always register the evaluation page so a QR scan lands on it directly (no "page not found").
    ui.hide_sidebar()
    nav = st.navigation([gate_page, evaluate_page])

nav.run()
