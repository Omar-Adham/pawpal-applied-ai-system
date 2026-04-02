from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler, Priority

# --- Setup ---
owner = Owner(name="Alex", available_minutes_per_day=90)

dog = Pet(name="Biscuit", species="Dog", age=3)
cat = Pet(name="Luna",    species="Cat", age=5, special_needs=["hyperthyroid medication"])

# --- Biscuit's tasks ---
dog.add_task(Task("Morning Walk",   category="walk",       duration_minutes=30,
                   priority=Priority.HIGH,   scheduled_time="07:00", frequency="daily"))
dog.add_task(Task("Breakfast",      category="feed",       duration_minutes=10,
                   priority=Priority.HIGH,   scheduled_time="08:00", frequency="daily"))
dog.add_task(Task("Fetch Session",  category="enrichment", duration_minutes=20,
                   priority=Priority.MEDIUM, scheduled_time="15:00", frequency="weekly"))

# --- Luna's tasks ---
# INTENTIONAL CONFLICT 1: Thyroid Meds at 07:00 — same slot as Biscuit's Morning Walk
cat.add_task(Task("Thyroid Meds",   category="meds",       duration_minutes=5,
                   priority=Priority.HIGH,   scheduled_time="07:00", frequency="daily"))
# INTENTIONAL CONFLICT 2: Dinner at 08:00 — same slot as Biscuit's Breakfast
cat.add_task(Task("Dinner",         category="feed",       duration_minutes=10,
                   priority=Priority.HIGH,   scheduled_time="08:00", frequency="daily"))
# No conflict — unique slot
cat.add_task(Task("Brush Coat",     category="grooming",   duration_minutes=15,
                   priority=Priority.LOW,    scheduled_time="18:00", frequency="weekly"))

owner.add_pet(dog)
owner.add_pet(cat)

scheduler = Scheduler(owner)

# ── Step 4: conflict detection ──────────────────────────────────────────────
print("=" * 56)
print("  CONFLICT DETECTION")
print("=" * 56)
conflicts = scheduler.detect_conflicts()
if conflicts:
    for warning in conflicts:
        print(f"  {warning}")
else:
    print("  No conflicts found.")

# ── Full task list sorted by time ───────────────────────────────────────────
print()
print("=" * 56)
print("  ALL TASKS - sorted by scheduled_time")
print("=" * 56)
all_tasks = scheduler.get_all_tasks()
for task in scheduler.sort_by_time(all_tasks):
    pet_label = next(
        (p.name for p in owner.pets if task in p.tasks), "?"
    )
    print(f"  {task.scheduled_time}  [{pet_label:>7}]  {task!r}")

# ── Recurring task demo ─────────────────────────────────────────────────────
print()
print("=" * 56)
print("  RECURRING TASK - complete 'Thyroid Meds' (daily)")
print("=" * 56)
next_meds = scheduler.complete_task("Luna", "Thyroid Meds")
print(f"  Completed. Next occurrence: {next_meds!r}")
print(f"  Today: {date.today()}  |  Next due: {date.today() + timedelta(days=1)}")

# ── Re-check conflicts after rescheduling ───────────────────────────────────
print()
print("=" * 56)
print("  CONFLICT RE-CHECK (after Thyroid Meds rescheduled)")
print("=" * 56)
conflicts = scheduler.detect_conflicts()
if conflicts:
    for warning in conflicts:
        print(f"  {warning}")
else:
    print("  No conflicts found.")

# ── Generate today's plan ───────────────────────────────────────────────────
plan = scheduler.generate_plan()
print()
print("=" * 56)
print(f"  TODAY'S SCHEDULE FOR {owner.name.upper()}")
print(f"  Available: {owner.available_minutes_per_day} min  |  Used: {plan.total_time_used} min")
print("=" * 56)
for task in scheduler.sort_by_time(plan.scheduled):
    pet_label = next((p.name for p in owner.pets if task in p.tasks), "?")
    print(
        f"  {task.scheduled_time}  [{pet_label:>7}]  "
        f"{task.name:<20} {task.duration_minutes:>3} min  |  {task.priority.name}"
    )
if plan.skipped:
    print("\n  SKIPPED:")
    for task in plan.skipped:
        print(f"    {task.name:<24} - {plan.reasoning.get(task.name, 'unknown')}")
print("=" * 56)
