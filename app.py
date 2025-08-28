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
st.write("Track daily study tanpa Articles (hanya modul+durasi).")

# --- Step 0: Initialize session state ---
if "classes" not in st.session_state:
    st.session_state.classes = []
if "schedule" not in st.session_state:
    st.session_state.schedule = {}

# --- Step 1: Set Date Range ---
st.header("1. Set Date Range")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime.date.today())
with col2:
    end_date = st.date_input("End Date", datetime.date.today() + datetime.timedelta(days=7))

# --- Step 2: Add Classes and Modules ---
st.header("2. Add Classes and Modules")
class_name = st.text_input("Enter Class Name")
if st.button("➕ Add Class"):
    if class_name:
        st.session_state.classes.append({"name": class_name, "modules": []})

for class_idx, class_item in enumerate(st.session_state.classes):
    with st.expander(f"📘 Class: {class_item['name']}", expanded=False):
        module_input = st.text_area(
            f"Add Modules and Duration (min) for {class_item['name']} (one per line, e.g. `Module Title 60`)",
            key=f"module_{class_idx}"
        )
        if st.button(f"➕ Save Modules to {class_item['name']}", key=f"add_module_{class_idx}"):
            msg_placeholder = st.empty()
            added_any = False

            for line in module_input.splitlines():
                match = re.match(r"(.+?)\s+(\d+)$", line.strip())
                if match:
                    title, duration = match.groups()
                    if any(m['name'].lower() == title.strip().lower() for m in class_item["modules"]):
                        msg_placeholder.error(f'❌ Module "{title.strip()}" already exists!')
                    else:
                        class_item["modules"].append({"name": title.strip(), "duration": int(duration)})
                        msg_placeholder.success(f'✅ Module "{title.strip()}" ({duration} min) added!')
                        added_any = True

                    time.sleep(1.5)
                    msg_placeholder.empty()

            if not added_any and not class_item["modules"]:
                msg_placeholder.warning("No valid modules were added.")

        # tampilkan modul yg udah ditambahkan
        for module in class_item["modules"]:
            st.write(f"📂 **{module['name']}** ({module['duration']} min)")

# --- Step 3: Generate To-Do List ---
st.header("3. Generate To-Do List")
generate = st.button("📅 Generate Schedule")

if generate:
    all_tasks = []
    for class_item in st.session_state.classes:
        for module_item in class_item["modules"]:
            all_tasks.append({
                "class": class_item["name"],
                "module": module_item["name"],
                "duration": module_item["duration"]
            })

    total_days = (end_date - start_date).days + 1
    minutes_per_day = 5.5 * 60
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

    st.subheader("📌 Your Daily To-Do List")
    for day, tasks in schedule.items():
        total_minutes = sum(t["duration"] for t in tasks)
        total_hours = total_minutes / 60
        expander_title = f"📅 **{day.strftime('%A, %d %B %Y')}** ({total_minutes} min (~{total_hours:.1f} hr))" if tasks else f"📅 **{day.strftime('%A, %d %B %Y')}** (0 min)"
        with st.expander(expander_title):
            if tasks:
                for t in tasks:
                    st.write(f"✅ **{t['class']} → {t['module']}** ({t['duration']} min)")
            else:
                st.write("🎉 Free day!")

# --- Step 4: Export Excel ---
if st.session_state.schedule:
    st.header("4. Export Schedule to Excel")
    export_data = []
    for day, tasks in st.session_state.schedule.items():
        for t in tasks:
            export_data.append({
                "Date": day.strftime("%Y-%m-%d"),
                "Class": t["class"],
                "Module": t["module"],
                "Duration (min)": t["duration"],
            })

    df_export = pd.DataFrame(export_data)

    # Hitung total durasi per hari
    df_total = df_export.groupby("Date", as_index=False)["Duration (min)"].sum()
    df_total = df_total.rename(columns={"Duration (min)": "Total Duration (min/day)"})

    # Merge ke df utama
    df_export = df_export.merge(df_total, on="Date", how="left")

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

        # merge Date, Class, Module
        merge_column_in_rows(ws, "A", start_row, end_row)
        merge_column(ws, "B", start_row, end_row)
        merge_column(ws, "C", start_row, end_row)
        # merge Total Duration (kolom E)
        merge_column_in_rows(ws, "E", start_row, end_row)

        current_row += 1

    # Apply border + alignment + wrap_text, skip header row
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.border = thin_border
            col_letter = get_column_letter(cell.column)
            if col_letter == "C":  # Module
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    output_merged = BytesIO()
    wb.save(output_merged)
    excel_data = output_merged.getvalue()

    st.download_button(
        label="📥 Download Schedule (Excel)",
        data=excel_data,
        file_name="study_schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
