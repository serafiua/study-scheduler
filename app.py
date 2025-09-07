import streamlit as st
import datetime
import re
import time
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Side
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="Study Scheduler", layout="wide")

st.title("📚 Study Scheduler")
st.write("Organize your study tasks efficiently (~6h/day).")

# --- Step 0: Initialize session state ---
if "classes" not in st.session_state:
    st.session_state.classes = []
if "schedule" not in st.session_state:
    st.session_state.schedule = {}

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ Setup Schedule")

    # --- Step 1: Set Date Range ---
    st.subheader("1. Set Date Range")

    start_date = st.date_input("Start Date", datetime.date.today(), key="start_date")
    end_date = st.date_input("End Date", key="end_date")
    if end_date < start_date:
        st.error("⚠️ End Date cannot be earlier than Start Date.")
        
    # --- Step 2: Add Classes and Modules ---
    st.subheader("2. Add Classes and Modules")

    # Input Class
    class_input = st.text_input("Enter Class Name", key="class_input", placeholder="e.g., Mathematics")
    msg_class_placeholder = st.empty()

    if st.button("➕ Add Class", key="save_class", use_container_width=True):
        if class_input.strip():
            if any(c['name'].lower() == class_input.strip().lower() for c in st.session_state.classes):
                msg_class_placeholder.error(f'❌ Class already exists!')
            else:
                st.session_state.classes.append({"name": class_input.strip(), "modules": []})
                msg_class_placeholder.success(f'✅ Class added!')
            time.sleep(1.2)
            msg_class_placeholder.empty()
        else:
            msg_class_placeholder.warning("⚠️ Class name cannot be empty.")

    # Loop Classes
    for class_idx, class_item in enumerate(st.session_state.classes):
        with st.expander(f"📘 Class: {class_item['name']}", expanded=False):

            module_input = st.text_input(
                f"Enter Module Name for Class `{class_item['name']}`",
                key=f"module_input_{class_idx}",
                placeholder="e.g., Algebra"
            )
            msg_module_placeholder = st.empty()

            if st.button("➕ Add Module", key=f"save_module_{class_idx}", use_container_width=True):
                if module_input.strip():
                    if any(m['name'].lower() == module_input.strip().lower() for m in class_item["modules"]):
                        msg_module_placeholder.error(f'❌ Module already exists!')
                    else:
                        class_item["modules"].append({"name": module_input.strip(), "articles": []})
                        msg_module_placeholder.success(f'✅ Module added!')
                    time.sleep(1.2)
                    msg_module_placeholder.empty()
                else:
                    msg_module_placeholder.warning("⚠️ Module name cannot be empty.")

            # Loop Modules
            for module_idx, module_item in enumerate(class_item["modules"]):
                with st.expander(f"📂 Module: {module_item['name']}", expanded=False):

                    article_input = st.text_area(
                        f"Add Articles and Duration (minute) for Module `{module_item['name']}` "
                        "(format: `Article Title(space)Duration`)",
                        key=f"articles_{class_idx}_{module_idx}",
                        placeholder="Article Title 10\nAnother Title 15"
                    )
                    msg_article_placeholder = st.empty()

                    if st.button("➕ Add Articles", key=f"save_articles_{class_idx}_{module_idx}", use_container_width=True):
                        added_any = False
                        for line in article_input.splitlines():
                            match = re.match(r"(.+?)\s+(\d+)$", line.strip())
                            if match:
                                title, duration = match.groups()
                                if any(a['title'].lower() == title.strip().lower() for a in module_item["articles"]):
                                    msg_article_placeholder.error(f'❌ "{title.strip()}" already exists!')
                                else:
                                    module_item["articles"].append({"title": title.strip(), "duration": int(duration)})
                                    msg_article_placeholder.success(f'✅ "{title.strip()}" ({duration} min) added!')
                                    added_any = True

                                time.sleep(1.2)
                                msg_article_placeholder.empty()

                        if not added_any and not module_item["articles"]:
                            msg_article_placeholder.warning("⚠️ No valid articles were added.")

                    # List articles added
                    st.markdown("""
                        <style>
                        div.stButton > button:first-child {
                            padding: 0px 6px;
                            height: 1.2em;
                            font-size: 12px;
                            line-height: 1.2em;
                        }
                        </style>
                    """, unsafe_allow_html=True)

                    if module_item["articles"]:
                        st.markdown("**📑 Articles in this module:**\n\n*(Click the button to remove the article)*")
                        for art_idx, art in enumerate(module_item["articles"]):
                            if st.button(f"• **{art['title']}** ({art['duration']} min)   🗑️",
                                        key=f"del_article_{class_idx}_{module_idx}_{art_idx}"):
                                module_item["articles"].pop(art_idx)
                                st.rerun()

    # --- Step 3: Generate Schedule ---
    st.subheader("3. Generate Schedule")

    if end_date < start_date:
        generate = st.button("📅 Generate", disabled=True, use_container_width=True)
        st.warning("⚠️ Please choose an End Date that is the same or after the Start Date.")
    elif not st.session_state.classes or all(
        not class_item["modules"] or all(not module_item["articles"] for module_item in class_item["modules"])
        for class_item in st.session_state.classes):
        generate = st.button("📅 Generate", disabled=True, use_container_width=True)
        st.info("Please add at least one class with modules and articles before generating the schedule.")
    else:
        generate = st.button("📅 Generate", use_container_width=True)

# ========== MAIN CONTENT ==========
tab1, tab2, tab3 = st.tabs(["Preview", "Markdown", "Excel"])

with tab1:
    if generate:
        all_tasks = []
        for class_item in st.session_state.classes:
            for module_item in class_item["modules"]:
                for article in module_item["articles"]:
                    all_tasks.append({
                        "class": class_item["name"],
                        "module": module_item["name"],
                        "title": article["title"],
                        "duration": article["duration"]
                    })

        total_days = (end_date - start_date).days + 1
        minutes_per_day = 5 * 60
        schedule = {start_date + datetime.timedelta(days=i): [] for i in range(total_days)}

        current_day = start_date
        used_minutes = 0

        for task in all_tasks:
            if used_minutes + task["duration"] > minutes_per_day:
                current_day += datetime.timedelta(days=1)
                used_minutes = 0
            if current_day > end_date:
                st.error("⚠️ The schedule cannot fit within the given date range. Try extending the dates.")
                break
            schedule[current_day].append(task)
            used_minutes += task["duration"]

        st.session_state.schedule = schedule

    if st.session_state.schedule:
        st.subheader("Your Schedule")
        for day, tasks in st.session_state.schedule.items():
            total_minutes = sum(t["duration"] for t in tasks)
            total_hours = total_minutes / 60
            expander_title = (
                f"📅 **{day.strftime('%A, %d %B %Y')}** "
                f"({total_minutes} min ~{total_hours:.1f} hr)"
                if tasks else f"📅 **{day.strftime('%A, %d %B %Y')}** (0 min)"
            )
            with st.expander(expander_title):
                if tasks:
                    for t in tasks:
                        st.write(f"✅ **{t['class']} → {t['module']} → {t['title']}** ({t['duration']} min)")
                else:
                    st.write("🎉 Free day!")

    else:
        st.info("ℹ️ Generate schedule first in the sidebar to create your study schedule.")

with tab2:
    if st.session_state.schedule:
        st.subheader("Copy-Paste Markdown")
        markdown_text = ""
        for day, tasks in st.session_state.schedule.items():
            total_minutes = sum(t["duration"] for t in tasks)
            total_hours = total_minutes / 60
            markdown_text += f"### 📅 {day.strftime('%A, %d %B %Y')}  \n"
            markdown_text += f"**Total:** {total_minutes} min (~{total_hours:.1f} hr)\n\n"
            if tasks:
                for t in tasks:
                    markdown_text += f"- ✅ **{t['class']} → {t['module']} → {t['title']}** ({t['duration']} min)\n"
            else:
                markdown_text += "- 🎉 Free day!\n"
            markdown_text += "\n"

        st.code(markdown_text, language="markdown")
    else:
        st.info("ℹ️ Generate schedule first in the sidebar.")

with tab3:
    if st.session_state.schedule:
        # --- Export Excel ---
        export_data = []
        for day, tasks in st.session_state.schedule.items():
            total_minutes_day = sum(t["duration"] for t in tasks) if tasks else 0
            for t in tasks:
                export_data.append({
                    "Date": day.strftime("%d-%m-%Y"),
                    "Class": t["class"],
                    "Module": t["module"],
                    "Article": t["title"],
                    "Duration (min)": t["duration"],
                    "Total Duration (min/day)": total_minutes_day,
                    "Status (✅)": "☐"
                })
            if not tasks:
                export_data.append({
                    "Date": day.strftime("%d-%m-%Y"),
                    "Class": "-",
                    "Module": "-",
                    "Article": "-",
                    "Duration (min)": 0,
                    "Total Duration (min/day)": 0,
                    "Status (✅)": "☐"
                })

        df_export = pd.DataFrame(export_data)

        # --- Save as Excel ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Schedule")
        output.seek(0)

        wb = load_workbook(output)
        ws = wb["Schedule"]

        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                             top=Side(style='thin'), bottom=Side(style='thin'))

        def merge_column_in_rows(ws, col_letter, start_row, end_row):
            if end_row > start_row:
                ws.merge_cells(f"{col_letter}{start_row}:{col_letter}{end_row}")
                ws[f"{col_letter}{start_row}"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        def merge_column(ws, col_letter, start_row, end_row):
            row = start_row
            while row <= end_row:
                merge_start = row
                while row + 1 <= end_row and ws[f"{col_letter}{row}"].value == ws[f"{col_letter}{row+1}"].value:
                    row += 1
                merge_column_in_rows(ws, col_letter, merge_start, row)
                row += 1

        current_row = 2
        while current_row <= ws.max_row:
            date_value = ws[f"A{current_row}"].value
            start_row = current_row
            while current_row + 1 <= ws.max_row and ws[f"A{current_row+1}"].value == date_value:
                current_row += 1
            end_row = current_row

            merge_column_in_rows(ws, "A", start_row, end_row)
            merge_column(ws, "B", start_row, end_row)
            merge_column(ws, "C", start_row, end_row)
            merge_column_in_rows(ws, "F", start_row, end_row)

            current_row += 1

        # Apply border + alignment + wrap_text
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                cell.border = thin_border
                col_letter = get_column_letter(cell.column)
                if col_letter == "D" and cell.row != 1:
                    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                else:
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        output_merged = BytesIO()
        wb.save(output_merged)
        excel_data = output_merged.getvalue()

        # --- button download ---
        col1, col2 = st.columns([5, 2])
        with col1:
            st.subheader("Preview Excel Table")
        with col2:
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name="study_schedule.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # --- Preview table ---
        st.dataframe(df_export, use_container_width=True)

    else:
        st.info("ℹ️ Generate schedule first in the sidebar.")





