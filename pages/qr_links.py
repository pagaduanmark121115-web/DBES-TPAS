import pandas as pd
import streamlit as st

import auth
import core
import qr
import ui
from tpas_form import GRADE_LEVELS

auth.require_login()
ui.show_flash()
st.title("🔗 QR Codes & Links")
ui.base_url_warning()
st.caption("The QR code and the link open exactly the same evaluation form. Print QR codes only after the app "
           "is deployed and APP_BASE_URL is set.")

assignments = [a for a in core.list_assignments() if a["active"] and a["teacher_active"]]
if not assignments:
    st.info("No active assignments yet.")
    st.stop()

f1, f2 = st.columns(2)
grade = f1.selectbox("Grade level", ["All"] + GRADE_LEVELS)
names = sorted({a["teacher_name"] for a in assignments})
teacher = f2.selectbox("Teacher", ["All"] + names)
shown = [a for a in assignments
         if (grade == "All" or a["grade_level"] == grade) and (teacher == "All" or a["teacher_name"] == teacher)]

st.dataframe(
    pd.DataFrame([{"Teacher": a["teacher_name"], "Grade": a["grade_level"], "Subject": a["label"],
                   "Sections": ", ".join(s["name"] for s in a["sections"]),
                   "Link": core.build_link(a["token"])} for a in shown]),
    hide_index=True, column_config={"Link": st.column_config.LinkColumn("Link")})


def caption_lines(a):
    return [a["teacher_name"], a["label"], f"{a['grade_level']} - " + ", ".join(s["name"] for s in a["sections"])]


st.subheader("Preview one QR code")
if shown:
    pick = st.selectbox("Assignment", shown, key="qr_pick",
                        format_func=lambda x: f"{x['teacher_name']} | {x['grade_level']} | {x['label']}")
    link = core.build_link(pick["token"])
    png = qr.make_qr_png(link, caption_lines(pick))
    st.image(png, width=320)
    st.code(link, language=None)
    st.download_button("Download this QR code (PNG)", png,
                       file_name=qr.file_name(pick["teacher_name"], pick["grade_level"], pick["label"], pick["token"]),
                       mime="image/png")

st.subheader("Download all")
if shown and st.button(f"Prepare ZIP of {len(shown)} QR code(s)"):
    items = [(qr.file_name(a["teacher_name"], a["grade_level"], a["label"], a["token"]),
              qr.make_qr_png(core.build_link(a["token"]), caption_lines(a))) for a in shown]
    st.session_state["qr_zip"] = qr.zip_qr(items)
if st.session_state.get("qr_zip"):
    st.download_button("Download ZIP", st.session_state["qr_zip"], file_name="tpas_qr_codes.zip",
                       mime="application/zip")
