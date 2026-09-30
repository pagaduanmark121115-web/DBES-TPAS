import streamlit as st

import auth
import core
from tpas_form import CATEGORIES, COMMENT_FIELDS, FORM_TITLE, SCALE, SEMESTERS

st.markdown("<style>.block-container{max-width:860px;}</style>", unsafe_allow_html=True)

token = (st.query_params.get("t") or "").strip().upper()

st.title(f"📝 {FORM_TITLE}")
st.caption("TPAS Form 6")

if not token:
    st.info("Please scan the QR code or open the evaluation link given by your school.")
    st.stop()

a = core.get_assignment_by_token(token)
if not a or not a["active"] or not a["teacher_active"]:
    st.error("This evaluation link is not valid or is no longer active. Please ask HR for the correct QR code.")
    st.stop()
if core.get_setting("evaluation_open", "1") != "1":
    st.warning("Evaluations are currently closed.")
    st.stop()
sy = core.get_setting("school_year", "").strip()
if not sy:
    st.warning("Evaluations have not been opened yet. Please check back later.")
    st.stop()
if st.session_state.get(f"done_{token}"):
    st.success("Thank you! Your evaluation was submitted. You may now close this page.")
    st.stop()

sections = core.assignment_sections(a["id"])
if not sections:
    st.error("This evaluation is not fully set up yet. Please inform HR.")
    st.stop()

if auth.current_user():
    st.warning("You are logged in as HR. Anything you submit here counts as a real response.")

with st.container(border=True):
    st.markdown(f"**Teacher:** {a['teacher_name']}  \n**Subject:** {a['label']}  \n"
                f"**Grade level:** {a['grade_level']}  \n**School year:** {sy}")
st.info("**Rating scale:**  " + "  \u00b7  ".join(f"**{n}** \u2013 {SCALE[n]}" for n in (5, 4, 3, 2, 1)))
st.caption("Your email is used only to make sure you evaluate this teacher once per semester, and it is stored "
           "separately from your answers. Your ratings and comments are anonymous.")

section_names = {s["id"]: s["name"] for s in sections}

with st.form(f"eval_{token}"):
    c1, c2 = st.columns(2)
    semester = c1.selectbox("Semester", SEMESTERS, index=None, placeholder="Select semester")
    section_id = c2.selectbox("Your section", list(section_names), index=None, placeholder="Select your section",
                              format_func=lambda i: section_names[i])
    email = st.text_input("Your email address", placeholder="name@school-email.com")

    ratings = {}
    n = 0
    for cat in CATEGORIES:
        st.subheader(f"{cat['code']}. {cat['name']}")
        st.caption("The teacher\u2026")
        for text in cat["items"]:
            n += 1
            st.markdown(f"**{n}.** {text}")
            ratings[n] = st.segmented_control(f"Rating for statement {n}", [1, 2, 3, 4, 5],
                                              key=f"r_{token}_{n}", label_visibility="collapsed")

    st.subheader("E. Comments and Suggestions for the professional development of the teacher")
    st.caption("Optional.")
    comments = {}
    for col, label in COMMENT_FIELDS:
        comments[col] = st.text_area(label, key=f"c_{token}_{col}", height=90)

    submitted = st.form_submit_button("Submit evaluation", type="primary")

if submitted:
    ok, msg = core.submit_response(token, semester, section_id, email, ratings, comments)
    if ok:
        st.session_state[f"done_{token}"] = True
        st.rerun()
    else:
        st.error(msg)
