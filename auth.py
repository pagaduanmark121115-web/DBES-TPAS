"""HR login helpers."""
import streamlit as st

import core


def current_user():
    return st.session_state.get("user")


def require_login():
    if not current_user():
        st.warning("Please log in as HR to view this page.")
        st.stop()


def logout():
    st.session_state.pop("user", None)
    st.rerun()


def login_form():
    if st.session_state.get("_fails", 0) >= 5:
        st.error("Too many failed attempts. Reload the page to try again.")
        return
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        go = st.form_submit_button("Log in", type="primary")
    if go:
        if core.verify_user(username, password):
            st.session_state["user"] = username.strip()
            st.session_state["_fails"] = 0
            st.rerun()
        else:
            st.session_state["_fails"] = st.session_state.get("_fails", 0) + 1
            st.error("Incorrect username or password.")


def first_run_form():
    st.subheader("First-time setup: create the HR administrator account")
    st.caption("Do this right after deploying, before sharing the app link with anyone.")
    with st.form("create_admin"):
        username = st.text_input("Username")
        p1 = st.text_input("Password (at least 8 characters)", type="password")
        p2 = st.text_input("Confirm password", type="password")
        go = st.form_submit_button("Create account", type="primary")
    if go:
        if p1 != p2:
            st.error("Passwords do not match.")
            return
        ok, msg = core.create_user(username, p1)
        if ok:
            st.session_state["user"] = username.strip()
            st.rerun()
        else:
            st.error(msg)
