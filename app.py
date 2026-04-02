import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, Priority

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Persistent state vault — initialised once, survives every rerun
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None      # set when the owner form is submitted
if "current_pet" not in st.session_state:
    st.session_state.current_pet = None  # the pet tasks are being added to

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
    # Create Owner and Pet objects and wire them together
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

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        task_name = st.text_input("Task name", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col3:
        priority_str = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"])
    with col4:
        frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])

    if st.button("Add task"):
        task = Task(
            name=task_name,
            category="general",
            duration_minutes=int(duration),
            priority=Priority[priority_str],
            frequency=frequency,
        )
        try:
            pet.add_task(task)           # <-- calls Pet.add_task() from pawpal_system.py
            st.success(f"Added: {task_name}")
        except ValueError as e:
            st.error(str(e))

    # Show current task list for this pet
    if pet.tasks:
        st.write(f"**{pet.name}'s tasks:**")
        rows = [
            {
                "Task": t.name,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority.name,
                "Frequency": t.frequency,
                "Done": "✓" if t.is_completed else "",
            }
            for t in pet.tasks
        ]
        st.table(rows)
    else:
        st.info("No tasks yet — add one above.")

# ---------------------------------------------------------------------------
# Section 3 — Generate schedule
# ---------------------------------------------------------------------------
st.divider()
st.subheader("3. Generate Today's Schedule")

if st.session_state.owner is None:
    st.info("Complete setup first.")
elif not st.session_state.owner.get_all_tasks():
    st.info("Add at least one task before generating a schedule.")
else:
    if st.button("Generate schedule"):
        owner = st.session_state.owner
        scheduler = Scheduler(owner)          # <-- Scheduler from pawpal_system.py
        plan = scheduler.generate_plan()      # <-- runs the priority-first algorithm

        st.markdown(
            f"**{owner.name}'s plan — "
            f"{plan.total_time_used} / {owner.available_minutes_per_day} min used**"
        )

        if plan.scheduled:
            st.markdown("#### Scheduled")
            for task in plan.scheduled:
                st.markdown(f"- **{task.name}** — {task.duration_minutes} min | {task.priority.name}")

        if plan.skipped:
            st.markdown("#### Skipped")
            for task in plan.skipped:
                reason = plan.reasoning.get(task.name, "unknown reason")
                st.markdown(f"- ~~{task.name}~~ — {reason}")
