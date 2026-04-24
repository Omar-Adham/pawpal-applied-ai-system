import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, Priority
from rag import generate_advice

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

col_title, col_reset = st.columns([5, 1])
with col_title:
    st.title("🐾 PawPal+")
with col_reset:
    st.write("")
    if st.button("Start Over", type="secondary"):
        st.session_state.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# Persistent state vault — initialised once, survives every rerun
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None
if "current_pet" not in st.session_state:
    st.session_state.current_pet = None
if "plan" not in st.session_state:
    st.session_state.plan = None
if "pet_lookup" not in st.session_state:
    st.session_state.pet_lookup = {}
if "advice" not in st.session_state:
    st.session_state.advice = None

# ---------------------------------------------------------------------------
# Section 1 — Owner + Pet setup
# ---------------------------------------------------------------------------
st.subheader("1. Setup")

with st.form("setup_form"):
    owner_name = st.text_input("Your name", value="Jordan")
    available_time = st.number_input(
        "Minutes available today", min_value=10, max_value=480, value=90
    )
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
    pet_age = st.number_input("Pet age (years)", min_value=0, max_value=30, value=2)
    submitted = st.form_submit_button("Save owner & pet")

if submitted:
    owner = Owner(name=owner_name, available_minutes_per_day=int(available_time))
    pet = Pet(name=pet_name, species=species, age=int(pet_age))
    owner.add_pet(pet)
    st.session_state.owner = owner
    st.session_state.current_pet = pet
    st.session_state.plan = None
    st.session_state.advice = None
    st.success(f"Saved! Owner: {owner.name} | Pet: {pet.name} ({pet.species})")

# ---------------------------------------------------------------------------
# Section 2 — Add tasks to the pet
# ---------------------------------------------------------------------------
st.divider()
st.subheader("2. Add Tasks")

if st.session_state.current_pet is None:
    st.info("Complete setup above before adding tasks.")
else:
    pet = st.session_state.current_pet
    st.caption(f"Adding tasks for **{pet.name}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        task_name = st.text_input("Task name", value="Morning walk")
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col2:
        priority_str = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"])
        frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])
    with col3:
        scheduled_time = st.text_input("Scheduled time (HH:MM)", value="09:00")
        category = st.selectbox(
            "Category",
            ["walk", "feed", "meds", "grooming", "enrichment", "general"],
        )

    if st.button("Add task"):
        parts = scheduled_time.split(":")
        time_valid = (
            len(parts) == 2
            and parts[0].isdigit()
            and parts[1].isdigit()
            and 0 <= int(parts[0]) <= 23
            and 0 <= int(parts[1]) <= 59
        )
        if not task_name.strip():
            st.error("Task name cannot be empty.")
        elif not time_valid:
            st.error("Scheduled time must be in HH:MM format, e.g. 07:30.")
        else:
            task = Task(
                name=task_name,
                category=category,
                duration_minutes=int(duration),
                priority=Priority[priority_str],
                frequency=frequency,
                scheduled_time=scheduled_time,
            )
            try:
                pet.add_task(task)
                st.session_state.plan = None
                st.session_state.advice = None
                st.success(f"Added: {task_name} at {scheduled_time}")
            except ValueError as e:
                st.error(str(e))

    if pet.tasks:
        scheduler = Scheduler(st.session_state.owner)
        sorted_tasks = scheduler.sort_by_time(pet.tasks)

        st.write(f"**{pet.name}'s tasks** (sorted by time):")
        rows = [
            {
                "Time": t.scheduled_time,
                "Task": t.name,
                "Category": t.category,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority.name,
                "Frequency": t.frequency,
                "Done": "✓" if t.is_completed else "",
            }
            for t in sorted_tasks
        ]
        st.table(rows)
    else:
        st.info("No tasks yet — add one above.")

# ---------------------------------------------------------------------------
# Section 3 — Conflict check
# ---------------------------------------------------------------------------
st.divider()
st.subheader("3. Check for Conflicts")

if st.session_state.owner is None:
    st.info("Complete setup first.")
elif not st.session_state.owner.get_all_tasks():
    st.info("Add at least one task before checking conflicts.")
else:
    scheduler = Scheduler(st.session_state.owner)
    conflicts = scheduler.detect_conflicts()

    if conflicts:
        st.error(
            f"**{len(conflicts)} scheduling conflict(s) found.** "
            "Two or more tasks are assigned the same start time — "
            "you won't be able to do them both at once. "
            "Edit a task's scheduled time to resolve each conflict."
        )
        for warning in conflicts:
            time_part = warning.split("conflict at ")[-1].split(":")[0] + \
                        ":" + warning.split("conflict at ")[-1].split(":")[1].split(",")[0].strip()
            with st.expander(f"Conflict at {warning.split('conflict at ')[-1].split(':')[0]}:{warning.split('conflict at ')[-1].split(':')[1].split(',')[0].strip()}"):
                st.warning(warning)
                st.caption(
                    "Tip: open 'Add Tasks' above, remove one of these tasks, "
                    "and re-add it with a different start time."
                )
    else:
        st.success("No conflicts — every task has a unique start time.")

# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# ---------------------------------------------------------------------------
st.divider()
st.subheader("4. Generate Today's Schedule")

if st.session_state.owner is None:
    st.info("Complete setup first.")
elif not st.session_state.owner.get_all_tasks():
    st.info("Add at least one task before generating a schedule.")
else:
    if st.button("Generate schedule"):
        owner = st.session_state.owner
        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        pet_lookup = {}
        for p in owner.pets:
            for t in p.tasks:
                pet_lookup[t.name] = p.name

        st.session_state.plan = plan
        st.session_state.pet_lookup = pet_lookup

        with st.spinner("Fetching personalised advice..."):
            st.session_state.advice = generate_advice(plan, owner)

    plan = st.session_state.plan
    if plan:
        owner = st.session_state.owner
        pet_lookup = st.session_state.pet_lookup
        scheduler = Scheduler(owner)

        pct = int(plan.total_time_used / owner.available_minutes_per_day * 100) \
              if owner.available_minutes_per_day else 0
        st.markdown(
            f"**{owner.name}'s plan — "
            f"{plan.total_time_used} / {owner.available_minutes_per_day} min used ({pct}%)**"
        )
        st.progress(min(pct, 100))

        if plan.scheduled:
            st.markdown("#### Scheduled")
            sorted_scheduled = scheduler.sort_by_time(plan.scheduled)
            rows = [
                {
                    "Time": t.scheduled_time,
                    "Pet": pet_lookup.get(t.name, "—"),
                    "Task": t.name,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority.name,
                    "Frequency": t.frequency,
                }
                for t in sorted_scheduled
            ]
            st.table(rows)
            st.success(f"{len(plan.scheduled)} task(s) fit within your available time.")

        if plan.skipped:
            st.markdown("#### Skipped")
            for task in plan.skipped:
                reason = plan.reasoning.get(task.name, "unknown reason")
                if reason == "already completed":
                    st.info(f"**{task.name}** — already done today")
                else:
                    st.warning(f"**{task.name}** — {reason}")

        st.divider()
        st.markdown("#### 🐾 AI Care Advice")
        if st.session_state.advice:
            st.success(st.session_state.advice)

# ---------------------------------------------------------------------------
# Section 5 — Edit schedule
# ---------------------------------------------------------------------------
plan = st.session_state.plan
_skippable_check = [t for t in plan.skipped if plan.reasoning.get(t.name) != "already completed"] if plan else []
if plan and (plan.scheduled or _skippable_check):
    st.divider()
    st.subheader("5. Edit Schedule")

    owner = st.session_state.owner
    scheduler = Scheduler(owner)

    # Rebuild pet_lookup so tasks added after plan generation show the correct pet name
    pet_lookup = {}
    for p in owner.pets:
        for t in p.tasks:
            pet_lookup[t.name] = p.name
    st.session_state.pet_lookup = pet_lookup

    # --- Scheduled tasks ---
    if plan.scheduled:
        st.markdown("**Scheduled tasks** — uncheck Keep to remove from today's plan:")
        sorted_scheduled = scheduler.sort_by_time(plan.scheduled)
        scheduled_rows = [
            {
                "Keep": True,
                "Time": t.scheduled_time,
                "Pet": pet_lookup.get(t.name, "—"),
                "Task": t.name,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority.name,
            }
            for t in sorted_scheduled
        ]
        edited_scheduled = st.data_editor(
            scheduled_rows,
            key="edit_scheduled",
            column_config={
                "Keep": st.column_config.CheckboxColumn("Keep", default=True, width="small"),
                "Time": st.column_config.TextColumn("Time (HH:MM)", width="small"),
                "Pet": st.column_config.TextColumn("Pet", disabled=True, width="small"),
                "Task": st.column_config.TextColumn("Task", disabled=True),
                "Duration (min)": st.column_config.NumberColumn(
                    "Duration (min)", min_value=1, max_value=480, width="small"
                ),
                "Priority": st.column_config.SelectboxColumn(
                    "Priority", options=["HIGH", "MEDIUM", "LOW"], width="small"
                ),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
        )
    else:
        edited_scheduled = []

    # --- Skipped tasks ---
    skippable = [t for t in plan.skipped if plan.reasoning.get(t.name) != "already completed"]
    if skippable:
        st.markdown("**Skipped tasks** — check Add to put a task back in today's plan:")
        skipped_rows = [
            {
                "Add": False,
                "Time": t.scheduled_time,
                "Pet": pet_lookup.get(t.name, "—"),
                "Task": t.name,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority.name,
                "Reason": plan.reasoning.get(t.name, ""),
            }
            for t in skippable
        ]
        edited_skipped = st.data_editor(
            skipped_rows,
            key="edit_skipped",
            column_config={
                "Add": st.column_config.CheckboxColumn("Add", default=False, width="small"),
                "Time": st.column_config.TextColumn("Time (HH:MM)", width="small"),
                "Pet": st.column_config.TextColumn("Pet", disabled=True, width="small"),
                "Task": st.column_config.TextColumn("Task", disabled=True),
                "Duration (min)": st.column_config.NumberColumn(
                    "Duration (min)", min_value=1, max_value=480, width="small"
                ),
                "Priority": st.column_config.SelectboxColumn(
                    "Priority", options=["HIGH", "MEDIUM", "LOW"], width="small"
                ),
                "Reason": st.column_config.TextColumn("Reason", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
        )
    else:
        edited_skipped = []

    if st.button("Apply edits"):
        def to_records(data):
            return data.to_dict("records") if hasattr(data, "to_dict") else data

        scheduled_task_map = {t.name: t for t in plan.scheduled}
        skipped_task_map = {t.name: t for t in plan.skipped}
        errors = []
        new_scheduled = []
        new_skipped = list(plan.skipped)  # start with full skipped list; we'll patch it

        def validate_time(time_str, task_name):
            parts = str(time_str).split(":")
            if not (len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()
                    and 0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                errors.append(f"**{task_name}**: invalid time '{time_str}' — use HH:MM format.")
                return False
            return True

        # Process scheduled table
        for row in to_records(edited_scheduled):
            task = scheduled_task_map[row["Task"]]
            if not validate_time(row["Time"], task.name):
                continue
            task.scheduled_time = row["Time"]
            task.duration_minutes = int(row["Duration (min)"])
            task.priority = Priority[row["Priority"]]
            if row["Keep"]:
                new_scheduled.append(task)
            else:
                plan.reasoning[task.name] = "removed from schedule"
                if task not in new_skipped:
                    new_skipped.append(task)

        # Process skipped table — add checked tasks back to schedule
        for row in to_records(edited_skipped):
            if not row["Add"]:
                continue
            task = skipped_task_map[row["Task"]]
            if not validate_time(row["Time"], task.name):
                continue
            task.scheduled_time = row["Time"]
            task.duration_minutes = int(row["Duration (min)"])
            task.priority = Priority[row["Priority"]]
            plan.reasoning.pop(task.name, None)
            new_scheduled.append(task)
            new_skipped = [t for t in new_skipped if t.name != task.name]

        if errors:
            for msg in errors:
                st.error(msg)
        elif not new_scheduled:
            st.warning("This would remove all tasks from your schedule. Keep at least one task, or add a skipped task back.")
        else:
            plan.scheduled = new_scheduled
            plan.skipped = new_skipped
            plan.total_time_used = sum(t.duration_minutes for t in new_scheduled)
            st.session_state.plan = plan

            with st.spinner("Updating AI advice..."):
                st.session_state.advice = generate_advice(plan, owner)

            st.success("Schedule updated.")
            st.rerun()
