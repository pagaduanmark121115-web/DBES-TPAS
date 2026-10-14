import streamlit as st
from tpas_db import SCALE, SECTIONS, init_db, run, write

st.set_page_config(page_title="Student Evaluation of Teachers", page_icon="📝")
init_db()

st.title("TPAS Form 6")
st.subheader("Student Evaluation of Teachers")

st.markdown(
    "Rate each statement using this scale:  \n"
    + "  \n".join(f"**{k}** - {v}" for k, v in SCALE.items())
)

questions = run(
    "SELECT id, section, statement FROM tpas_questions WHERE is_active=1 ORDER BY section, sort_order, id"
)
if not questions:
    st.info("No questions have been added yet.")
    st.stop()

with st.form("form6"):
    c1, c2, c3 = st.columns(3)
    sy = c1.text_input("School Year (SY)", placeholder="2026-2027")
    school = c2.text_input("School")
    teacher = c3.text_input("Teacher being evaluated")

    for section in SECTIONS:
        items = [q for q in questions if q["section"] == section]
        if not items:
            continue
        st.markdown(f"### {section}")
        st.caption("The teacher...")
        for q in items:
            st.radio(
                q["statement"],
                options=list(SCALE.keys()),
                index=None,
                horizontal=True,
                key=f"q_{q['id']}",
            )

    st.markdown("### E. Comments and Suggestions for the professional development of the teacher's...")
    c_strategy = st.text_area("Teaching Strategy")
    c_classroom = st.text_area("Classroom Management")
    c_others = st.text_area("Others (please specify)")

    submitted = st.form_submit_button("Submit evaluation", type="primary")

if submitted:
    missing = [q for q in questions if st.session_state.get(f"q_{q['id']}") is None]
    if not (sy.strip() and teacher.strip()):
        st.error("Please enter the School Year and the teacher's name.")
    elif missing:
        st.error(f"Please rate all statements ({len(missing)} not yet answered).")
    else:
        eval_id = write([(
            "INSERT INTO tpas_evaluations (sy, school, teacher_name, comment_strategy, comment_classroom, comment_others) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sy.strip(), school.strip(), teacher.strip(), c_strategy.strip(), c_classroom.strip(), c_others.strip()),
        )])[0]
        write([
            ("INSERT INTO tpas_answers (evaluation_id, question_id, rating) VALUES (?, ?, ?)",
             (eval_id, q["id"], int(st.session_state[f"q_{q['id']}"])))
            for q in questions
        ])
        st.success("Thank you! Your evaluation has been submitted.")
        st.balloons()