import io

import pandas as pd
import streamlit as st

import auth
import core
import ui

auth.require_login()
ui.show_flash()
st.title("📥 Bulk Import")
st.caption("Load sections, teacher names, and each teacher's subjects from a spreadsheet instead of typing them "
           "one by one. Every upload is checked first; nothing is saved until you press Import.")

STATUS_LABEL = {"add": "✅ Will add", "merge": "➕ Will add sections", "update": "✏️ Will update",
                "skip": "⏭️ Already exists", "error": "❌ Problem"}


def excel_bytes(df):
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def template_buttons(df, base):
    c1, c2 = st.columns(2)
    c1.download_button("Download Excel template", excel_bytes(df), file_name=f"{base}_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"x_{base}")
    c2.download_button("Download CSV template", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{base}_template.csv", mime="text/csv", key=f"c_{base}")


def summary(plan):
    counts = {k: sum(1 for p in plan if p["status"] == k) for k in STATUS_LABEL}
    cols = st.columns(len(STATUS_LABEL))
    for col, (k, label) in zip(cols, STATUS_LABEL.items()):
        col.metric(label, counts[k])
    return counts


tab_s, tab_t, tab_a = st.tabs(["1. Sections & enrollment", "2. Teacher names", "3. Teachers & subjects"])

# ------------------------------------------------------- sections + enrollment
with tab_s:
    st.markdown("Columns: **Grade Level** (Grade 11 or Grade 12), **Section**, **Enrolled** (number of students).")
    template_buttons(core.section_template_df(), "sections")
    up = st.file_uploader("Upload sections file (.xlsx or .csv)", type=["xlsx", "csv"], key="up_sections")
    if up:
        try:
            plan, err = core.plan_section_import(core.read_table(up, up.name))
        except Exception as e:  # noqa: BLE001
            plan, err = None, f"Could not read the file: {e}"
        if err:
            st.error(err)
        else:
            counts = summary(plan)
            st.dataframe(pd.DataFrame([{"Row": p["row"], "Grade": p["grade"], "Section": p["section"],
                                        "Enrolled": p["enrolled"], "Result": STATUS_LABEL[p["status"]],
                                        "Note": p["note"]} for p in plan]), hide_index=True)
            if counts["error"]:
                st.warning("Rows marked ❌ will be skipped. Fix them in your file and upload again if needed.")
            if counts["add"] + counts["update"] and st.button("Import sections", type="primary"):
                done = core.apply_section_import(plan)
                ui.flash(f"Added {done['add']} section(s), updated {done['update']}.")
                st.rerun()

# ------------------------------------------------------------- teacher names
with tab_t:
    st.markdown("Paste teacher names, **one per line**. Names that already exist are skipped.")
    names = st.text_area("Teacher names", height=200, placeholder="Ms. Maria Reyes\nMr. Juan Santos\nMrs. Ana Cruz")
    if st.button("Add teachers", type="primary"):
        added, dup = core.add_teachers_bulk(names)
        if not added and not dup:
            st.error("Please paste at least one name.")
        else:
            msg = f"Added {len(added)} teacher(s)."
            if dup:
                msg += f" Skipped {len(dup)} that already exist."
            ui.flash(msg)
            st.rerun()
    st.caption("You can also skip this tab: teacher names in the Teachers & subjects file are created automatically.")

# ----------------------------------------------------- teachers + subjects
with tab_a:
    st.markdown(
        "Columns: **Teacher**, **Grade Level**, **Subject**, **Component** (optional), **Sections** "
        "(separate several with commas). One row per teacher, grade level and subject.\n\n"
        "For Life and Career Skills, use one row per teacher and put the component in the Component column "
        "(Personal Development, Physical Education, Religious Education). Writing "
        "*Life and Career Skills: Physical Education* in Subject also works.")
    template_buttons(core.assignment_template_df(), "teachers_subjects")
    create_secs = st.checkbox("Create sections that don't exist yet (enrollment starts at 0; set it later "
                              "under Sections & Enrollment)", value=True)
    up = st.file_uploader("Upload teachers & subjects file (.xlsx or .csv)", type=["xlsx", "csv"], key="up_assign")
    if up:
        try:
            plan, err = core.plan_assignment_import(core.read_table(up, up.name), create_sections=create_secs)
        except Exception as e:  # noqa: BLE001
            plan, err = None, f"Could not read the file: {e}"
        if err:
            st.error(err)
        else:
            counts = summary(plan)
            st.dataframe(pd.DataFrame([{
                "Row": p["row"], "Teacher": p["teacher"], "Grade": p["grade"],
                "Subject": core.subject_label(p["subject"], p["component"]),
                "Sections": ", ".join(p["sections"]), "Result": STATUS_LABEL[p["status"]], "Note": p["note"]}
                for p in plan]), hide_index=True)
            if counts["error"]:
                st.warning("Rows marked ❌ will be skipped. Fix them in your file and upload again if needed.")
            if counts["add"] + counts["merge"] and st.button("Import teachers & subjects", type="primary"):
                res = core.apply_assignment_import(plan)
                msg = (f"Added {res['added']} assignment(s), extended {res['merged']}, created "
                       f"{res['teachers']} teacher(s) and {res['sections']} section(s).")
                if res["failed"]:
                    ui.flash(msg + " Some rows failed: " + " | ".join(res["failed"]), "warning")
                else:
                    ui.flash(msg)
                st.rerun()
            st.caption("After importing, open QR Codes & Links to get each assignment's link and QR code.")
