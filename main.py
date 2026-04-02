from pawpal_system import Owner, Pet, Task, Scheduler, Priority

# --- Setup ---
owner = Owner(name="Alex", available_minutes_per_day=90)

dog = Pet(name="Biscuit", species="Dog", age=3)
cat = Pet(name="Luna", species="Cat", age=5, special_needs=["hyperthyroid medication"])

# --- Tasks for Biscuit ---
dog.add_task(Task("Morning Walk",   category="walk",       duration_minutes=30, priority=Priority.HIGH))
dog.add_task(Task("Breakfast",      category="feed",       duration_minutes=10, priority=Priority.HIGH))
dog.add_task(Task("Fetch Session",  category="enrichment", duration_minutes=20, priority=Priority.MEDIUM))

# --- Tasks for Luna ---
cat.add_task(Task("Thyroid Meds",   category="meds",       duration_minutes=5,  priority=Priority.HIGH))
cat.add_task(Task("Dinner",         category="feed",       duration_minutes=10, priority=Priority.HIGH))
cat.add_task(Task("Brush Coat",     category="grooming",   duration_minutes=15, priority=Priority.LOW))

# --- Register pets with owner ---
owner.add_pet(dog)
owner.add_pet(cat)

# --- Generate plan ---
scheduler = Scheduler(owner)
plan = scheduler.generate_plan()

# --- Print Today's Schedule ---
print("=" * 50)
print(f"  TODAY'S SCHEDULE FOR {owner.name.upper()}")
print(f"  Available time: {owner.available_minutes_per_day} min")
print("=" * 50)

print("\n  SCHEDULED TASKS")
print("  " + "-" * 40)
for task in plan.scheduled:
    pet_name = next(
        (p.name for p in owner.pets if task in p.tasks), "?"
    )
    print(f"  [{pet_name:>7}]  {task.name:<20} {task.duration_minutes:>3} min  |  {task.priority.name}")

print(f"\n  Total time used: {plan.total_time_used} / {owner.available_minutes_per_day} min")

if plan.skipped:
    print("\n  SKIPPED TASKS")
    print("  " + "-" * 40)
    for task in plan.skipped:
        reason = plan.reasoning.get(task.name, "unknown reason")
        print(f"  {task.name:<24} skipped — {reason}")

print("=" * 50)
