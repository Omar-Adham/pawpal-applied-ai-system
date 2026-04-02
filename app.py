import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, Priority

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Persistent state vault — initialised once, survives every rerun
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None
if "current_pet" not in st.session_state:
    st.session_state.current_pet = None

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

    if st.button("Add task"):
        # Basic HH:MM format guard
        parts = scheduled_time.split(":")
        time_valid = (
            len(parts) == 2
            and parts[0].isdigit()
            and parts[1].isdigit()
            and 0 <= int(parts[0]) <= 23
            and 0 <= int(parts[1]) <= 59
        )
        if not time_valid:
            st.error("Scheduled time must be in HH:MM format, e.g. 07:30.")
        else:
            task = Task(
                name=task_name,
                category="general",
                duration_minutes=int(duration),
                priority=Priority[priority_str],
                frequency=frequency,
                scheduled_time=scheduled_time,
            )
            try:
                pet.add_task(task)
                st.success(f"Added: {task_name} at {scheduled_time}")
            except ValueError as e:
                st.error(str(e))

    # Show task list sorted chronologically
    if pet.tasks:
        scheduler = Scheduler(st.session_state.owner)
        sorted_tasks = scheduler.sort_by_time(pet.tasks)

        st.write(f"**{pet.name}'s tasks** (sorted by time):")
        rows = [
            {
                "Time": t.scheduled_time,
                "Task": t.name,
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
            # Parse "WARNING - conflict at HH:MM: Pet:Task, Pet:Task"
            # and display each one as an expandable warning block
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

        # Time budget header
        pct = int(plan.total_time_used / owner.available_minutes_per_day * 100) \
              if owner.available_minutes_per_day else 0
        st.markdown(
            f"**{owner.name}'s plan — "
            f"{plan.total_time_used} / {owner.available_minutes_per_day} min used ({pct}%)**"
        )
        st.progress(min(pct, 100))

        # Scheduled tasks — sorted by time, shown in a table
        if plan.scheduled:
            st.markdown("#### Scheduled")
            sorted_scheduled = scheduler.sort_by_time(plan.scheduled)

            # Build pet-name lookup once
            pet_lookup = {}
            for p in owner.pets:
                for t in p.tasks:
                    pet_lookup[t.name] = p.name

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

        # Skipped tasks — with plain-English reasons
        if plan.skipped:
            st.markdown("#### Skipped")
            for task in plan.skipped:
                reason = plan.reasoning.get(task.name, "unknown reason")
                if reason == "already completed":
                    st.info(f"**{task.name}** — already done today")
                else:
                    st.warning(f"**{task.name}** — {reason}")
