import streamlit as st
import datetime
import re
import time
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Side

st.set_page_config(page_title="Study Scheduler", layout="wide")

st.title("📚 Study Scheduler")
st.write("Plan your study tasks into daily to-do lists.")

# --- Step 1: Set Date Range ---
st.header("1. Set Date Range")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime.date.today())
with col2:
    end_date = st.date_input("End Date", datetime.date.today() + datetime.timedelta(days=7))

# --- Step 2: Add Classes, Modules, and Articles ---
st.header("2. Add Classes and Modules")

if "classes" not in st.session_state:
    st.session_state.classes = []

# Add class
class_name = st.text_input("Enter Class Name")
if st.button("➕ Add Class"):
    if class_name:
        st.session_state.classes.append({"name": class_name, "modules": []})

# Show classes with modules & articles
for class_idx, class_item in enumerate(st.session_state.classes):
    with st.expander(f"📘 Class: {class_item['name']}", expanded=False):
        module_name = st.text_input(f"Add Module for {class_item['name']}", key=f"module_{class_idx}")
        if st.button(f"➕ Add Module to {class_item['name']}", key=f"add_module_{class_idx}"):
            if module_name:
                class_item["modules"].append({"name": module_name, "articles": []})

        for module_idx, module_item in enumerate(class_item["modules"]):
            with st.expander(f"📂 Module: {module_item['name']}", expanded=False):
                article_input = st.text_input(
                    f"Add Articles and Duration (min) for {module_item['name']} (one per line, e.g. `Article Title 10`)", 
                    key=f"articles_{class_idx}_{module_idx}"
                )
                if st.button(f"➕ Add Articles to {module_item['name']}", key=f"save_articles_{class_idx}_{module_idx}"):
                    msg_placeholder = st.empty()
                    added_any = False

                    for line in article_input.splitlines():
                        match = re.match(r"(.+?)\s+(\d+)$", line.strip())
                        if match:
                            title, duration = match.groups()
                            if any(a['title'].lower() == title.strip().lower() for a in module_item["articles"]):
                                msg_placeholder.error(f'❌ Article "{title.strip()}" already exists!')
                            else:
                                module_item["articles"].append({"title": title.strip(), "duration": int(duration)})
                                msg_placeholder.success(f'✅ Article "{title.strip()}" ({duration} min) has been successfully added!')
                                added_any = True

                            time.sleep(3)
                            msg_placeholder.empty()

                    if not added_any and not module_item["articles"]:
                        msg_placeholder.warning("No valid articles were added.")

# --- Step 3: Generate To-Do List ---
st.header("3. Generate To-Do List")

if "schedule" not in st.session_state:
    st.session_state.schedule = {}

generate = st.button("📅 Generate Schedule")

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
    minutes_per_day = 7 * 60
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

    # Display Schedule
    st.subheader("📌 Your Daily To-Do List")
    for day, tasks in schedule.items():
        total_minutes = sum(t["duration"] for t in tasks)
        total_hours = total_minutes / 60
        if tasks:
            expander_title = f"📅 **{day.strftime('%A, %d %B %Y')}** ({total_minutes} min (~{total_hours:.1f} hr))"
        else:
            expander_title = f"📅 **{day.strftime('%A, %d %B %Y')}** (0 min)"

        with st.expander(expander_title):
            if tasks:
                for t in tasks:
                    st.write(f"✅ **{t['class']} → {t['module']} → {t['title']}** ({t['duration']} min)")
            else:
                st.write("🎉 Free day!")

# --- Step 4: Export to Excel with merged cells per date & border ---
if st.session_state.schedule:
    export_data = []
    for day, tasks in st.session_state.schedule.items():
        for t in tasks:
            export_data.append({
                "Date": day.strftime("%Y-%m-%d"),
                "Class": t["class"],
                "Module": t["module"],
                "Article": t["title"],
                "Duration (min)": t["duration"],
                "Status (✅)": "☐"
            })

    df_export = pd.DataFrame(export_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Schedule")

    output.seek(0)
    wb = load_workbook(output)
    ws = wb["Schedule"]

    # Border style
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                         top=Side(style='thin'), bottom=Side(style='thin'))

    # Merge function
    def merge_column_in_rows(ws, col_letter, start_row, end_row):
        if end_row > start_row:
            ws.merge_cells(f"{col_letter}{start_row}:{col_letter}{end_row}")
            ws[f"{col_letter}{start_row}"].alignment = Alignment(vertical="center", horizontal="center")

    def merge_column(ws, col_letter, start_row, end_row):
        row = start_row
        while row <= end_row:
            merge_start = row
            while row + 1 <= end_row and ws[f"{col_letter}{row}"].value == ws[f"{col_letter}{row+1}"].value:
                row += 1
            merge_column_in_rows(ws, col_letter, merge_start, row)
            row += 1

    # Merge per tanggal
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

        current_row += 1

    # Apply border to all cells
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.border = thin_border

    # Save to BytesIO
    output_merged = BytesIO()
    wb.save(output_merged)
    excel_data = output_merged.getvalue()

    st.download_button(
        label="📥 Download Schedule (Excel)",
        data=excel_data,
        file_name="study_schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
