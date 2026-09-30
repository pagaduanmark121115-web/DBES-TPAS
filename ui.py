"""Small Streamlit helpers shared by the pages."""
import streamlit as st

import core
import db


def flash(message, kind="success"):
    """Queue a message to show after the next st.rerun()."""
    st.session_state["_flash"] = (kind, message)


def show_flash():
    f = st.session_state.pop("_flash", None)
    if f:
        getattr(st, f[0])(f[1])


def hide_sidebar():
    st.markdown(
        "<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl'],"
        "[data-testid='collapsedControl']{display:none !important;}</style>",
        unsafe_allow_html=True)


def dev_mode_banner():
    if db.is_local():
        st.warning("DEVELOPMENT MODE: no Turso database is configured, so data is stored in a temporary "
                   "local file and will be lost when the app restarts. Add TURSO_DATABASE_URL and "
                   "TURSO_AUTH_TOKEN to the app secrets.")


def base_url_warning():
    if "localhost" in core.base_url():
        st.warning("APP_BASE_URL is still set to localhost, so links and QR codes generated now will NOT "
                   "work for students. Set APP_BASE_URL to your deployed app address in the app secrets "
                   "before printing any QR code.")
