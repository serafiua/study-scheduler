import streamlit as st
import datetime
import re
import time
import pandas as pd
from io import BytesIO

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
                    articles = []
                    for line in article_input.splitlines():
                        match = re.match(r"(.+?)\s+(\d+)$", line.strip())
                        if match:
                            title, duration = match.groups()
                            articles.append({"title": title.strip(), "duration": int(duration)})
                            # ✅ Temporary feedback message 
                            msg_placeholder = st.empty()
                            msg_placeholder.success(f'Article "{title.strip()}" with duration {duration} minutes has been successfully added!')
                            time.sleep(3)
                            msg_placeholder.empty()
                    module_item["articles"].extend(articles)

# --- Step 3: Generate To-Do List ---
st.header("3. Generate To-Do List")

if "schedule" not in st.session_state:
    st.session_state.schedule = {}

generate = st.button("📅 Generate Schedule")

if generate:
    # Collect all tasks
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
    minutes_per_day = 6 * 60  # 6 hours per day
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

    # save to session state
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

# --- Step 4: Export to Excel ---
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
                "Status": "☐"  # default unchecked box
            })

    df_export = pd.DataFrame(export_data)

    # Save to Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Schedule")
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Download Schedule (Excel)",
        data=excel_data,
        file_name="study_schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

