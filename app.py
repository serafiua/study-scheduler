import streamlit as st
from datetime import datetime, timedelta

# -----------------
# Data structures
# -----------------
class Article:
    def __init__(self, title, duration):
        self.title = title
        self.duration = duration  # in minutes

class Module:
    def __init__(self, title):
        self.title = title
        self.articles = []

class Class:
    def __init__(self, title):
        self.title = title
        self.modules = []

# -----------------
# App logic
# -----------------
def distribute_articles(classes, start_date, end_date, daily_limit=360):
    # Flatten all articles into a list preserving hierarchy
    tasks = []
    for c in classes:
        for m in c.modules:
            for a in m.articles:
                tasks.append((c.title, m.title, a.title, a.duration))

    # Generate date range
    num_days = (end_date - start_date).days + 1
    days = [start_date + timedelta(days=i) for i in range(num_days)]

    # Allocate articles per day with 6h/day max
    plan = {day: [] for day in days}
    day_idx = 0
    used_today = 0

    for task in tasks:
        c_title, m_title, a_title, duration = task

        # If doesn't fit in today's remaining time, move to next day
        while day_idx < len(days):
            if used_today + duration <= daily_limit:
                plan[days[day_idx]].append(task)
                used_today += duration
                break
            else:
                # Move to next day
                day_idx += 1
                used_today = 0
        else:
            # If out of days, put remaining into last day (overflow)
            plan[days[-1]].append(task)

    return plan

# -----------------
# Streamlit UI
# -----------------
st.title("📅 Study Scheduler (6h/day)")

# Input: Date range
st.header("1. Set Date Range")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start date", datetime.today())
with col2:
    end_date = st.date_input("End date", datetime.today() + timedelta(days=6))

# Classes input
st.header("2. Add Classes and Modules")

if "classes" not in st.session_state:
    st.session_state.classes = []

new_class = st.text_input("Add a new class title")
if st.button("➕ Add Class"):
    if new_class.strip():
        st.session_state.classes.append(Class(new_class.strip()))

# Display all classes
for idx_c, c in enumerate(st.session_state.classes):
    st.subheader(f"📘 Class: {c.title}")

    # Add module to this class
    new_module = st.text_input(f"Add module to {c.title}", key=f"module_{idx_c}")
    if st.button(f"➕ Add Module to {c.title}", key=f"add_module_{idx_c}"):
        if new_module.strip():
            c.modules.append(Module(new_module.strip()))

    # Display modules
    for idx_m, m in enumerate(c.modules):
        st.markdown(f"**📂 Module: {m.title}**")

        # Add article
        new_article = st.text_input(f"Article title,duration(min) for {m.title}", key=f"art_{idx_c}_{idx_m}")
        if st.button(f"➕ Add Article to {m.title}", key=f"add_art_{idx_c}_{idx_m}"):
            if "," in new_article:
                title, dur = new_article.split(",", 1)
                try:
                    duration = int(dur.strip())
                    m.articles.append(Article(title.strip(), duration))
                except ValueError:
                    st.error("Duration must be an integer (minutes)")

        # Show articles
        for a in m.articles:
            st.write(f"📝 {a.title} ({a.duration} min)")

# Generate plan
if st.button("✅ Generate Study Plan"):
    if not st.session_state.classes:
        st.warning("Please add at least one class with modules and articles!")
    else:
        plan = distribute_articles(st.session_state.classes, start_date, end_date)

        st.header("📆 Your Daily Study Plan")
        for day, tasks in plan.items():
            if tasks:
                total = sum(t[3] for t in tasks)
                st.subheader(f"{day} - Total {total} min (~{total//60}h {total%60}m)")
                for t in tasks:
                    st.write(f"- {t[0]} → {t[1]} → {t[2]} ({t[3]} min)")
            else:
                st.subheader(f"{day} - Free Day 🎉")
