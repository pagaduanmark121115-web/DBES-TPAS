import pandas as pd
import streamlit as st
from tpas_db import SECTIONS, init_db, require_admin, run, write

st.set_page_config(page_title="Form 6 Questions", page_icon="⚙️", layout="wide")
init_db()
require_admin()

st.title("TPAS Form 6 - Guide Questions")
st.caption("Add or edit the statements students will rate. Untick 'Active' to hide a statement without deleting it.")

# ---- Add a new statement ----
st.subheader("Add a statement")
with st.form("add_question", clear_on_submit=True):
    section = st.selectbox("Section", SECTIONS)
    statement = st.text_area("Statement (continues 'The teacher...')")
    order = st.number_input("Order within section", min_value=0, step=1, value=0)
    if st.form_submit_button("Add statement"):
        if statement.strip():
            write([(
                "INSERT INTO tpas_questions (section, statement, sort_order) VALUES (?, ?, ?)",
                (section, statement.strip(), int(order)),
            )])
            st.success("Statement added.")
            st.rerun()
        else:
            st.error("Please type a statement.")

# ---- Edit existing statements ----
st.subheader("Edit statements")
rows = run("SELECT id, section, statement, sort_order, is_active FROM tpas_questions ORDER BY section, sort_order, id")
df = pd.DataFrame(rows, columns=["id", "section", "statement", "sort_order", "is_active"])
df["is_active"] = df["is_active"].astype(bool)

edited = st.data_editor(
    df,
    hide_index=True,
    disabled=["id"],
    use_container_width=True,
    column_config={
        "section": st.column_config.SelectboxColumn("Section", options=SECTIONS, required=True),
        "statement": st.column_config.TextColumn("Statement", width="large", required=True),
        "sort_order": st.column_config.NumberColumn("Order", step=1),
        "is_active": st.column_config.CheckboxColumn("Active"),
    },
    key="q_editor",
)

if st.button("Save changes", type="primary"):
    stmts = [
        (
            "UPDATE tpas_questions SET section=?, statement=?, sort_order=?, is_active=? WHERE id=?",
            (r.section, r.statement.strip(), int(r.sort_order or 0), 1 if r.is_active else 0, int(r.id)),
        )
        for r in edited.itertuples()
    ]
    write(stmts)
    st.success("Saved.")
    st.rerun()
