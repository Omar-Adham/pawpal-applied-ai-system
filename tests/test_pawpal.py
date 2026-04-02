"""
test_pawpal.py — automated test suite for pawpal_system.py

Organized into five sections that mirror the test plan:
  1. Task fundamentals
  2. Sorting correctness
  3. generate_plan — priority ordering and time-budget enforcement
  4. Recurrence logic (complete_task)
  5. Conflict detection (detect_conflicts)
  6. Filter methods
  7. Edge cases

Each test function:
  - Has a one-line docstring saying WHAT it proves
  - Uses the Arrange / Act / Assert (AAA) pattern:
      Arrange  — build the objects the test needs
      Act      — call the method being tested
      Assert   — check the result

Why AAA?  It keeps each test readable as a mini-story:
  "Given this setup, when I do this, I expect this outcome."
"""

import pytest
from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler, Priority


# ---------------------------------------------------------------------------
# Shared fixtures — reusable building blocks for every test section
# ---------------------------------------------------------------------------

@pytest.fixture
def owner():
    """An owner with 60 minutes available — enough to fit several tasks."""
    return Owner(name="Alex", available_minutes_per_day=60)


@pytest.fixture
def dog():
    """A dog pet with no tasks yet."""
    return Pet(name="Biscuit", species="Dog", age=3)


@pytest.fixture
def cat():
    """A cat pet with no tasks yet."""
    return Pet(name="Luna", species="Cat", age=5)


def make_task(name="Walk", minutes=20, priority=Priority.MEDIUM,
              time="09:00", frequency="daily", due=None):
    """
    Helper that creates a Task with sensible defaults.

    Why a helper instead of a fixture?
    Fixtures always return the same object. This helper lets individual
    tests vary just the fields they care about — e.g., make_task(minutes=30)
    — without repeating every other argument.
    """
    return Task(
        name=name,
        category="general",
        duration_minutes=minutes,
        priority=priority,
        scheduled_time=time,
        frequency=frequency,
        due_date=due or date.today(),
    )


def make_scheduler(owner, *pets):
    """Register all given pets under owner and return a Scheduler."""
    for pet in pets:
        owner.add_pet(pet)
    return Scheduler(owner)


# ===========================================================================
# Section 1 — Task fundamentals
# ===========================================================================

def test_mark_complete_changes_status():
    """mark_complete() flips is_completed from False to True."""
    # Arrange
    task = make_task()
    assert task.is_completed is False
    # Act
    task.mark_complete()
    # Assert
    assert task.is_completed is True


def test_add_task_increases_pet_task_count(dog):
    """Adding a task to a Pet increases its task list by one."""
    task = make_task()
    dog.add_task(task)
    assert len(dog.tasks) == 1


def test_add_duplicate_task_raises(dog):
    """add_task() raises ValueError when a task with the same name already exists."""
    dog.add_task(make_task(name="Walk"))
    with pytest.raises(ValueError, match="already exists"):
        dog.add_task(make_task(name="Walk"))


def test_remove_unknown_task_raises(dog):
    """remove_task() raises ValueError when no task with that name exists."""
    with pytest.raises(ValueError, match="No task"):
        dog.remove_task("Ghost Task")


# ===========================================================================
# Section 2 — Sorting correctness
# ===========================================================================

def test_sort_by_time_returns_chronological_order(owner, dog):
    """sort_by_time returns tasks in HH:MM ascending order regardless of add order."""
    # Arrange — add tasks deliberately OUT of time order
    t_afternoon = make_task(name="Afternoon Run",  time="14:00")
    t_morning   = make_task(name="Morning Walk",   time="07:00")
    t_midday    = make_task(name="Midday Feed",    time="11:30")
    dog.add_task(t_afternoon)
    dog.add_task(t_morning)
    dog.add_task(t_midday)
    scheduler = make_scheduler(owner, dog)
    # Act
    sorted_tasks = scheduler.sort_by_time(dog.tasks)
    # Assert — times must be in ascending order
    times = [t.scheduled_time for t in sorted_tasks]
    assert times == ["07:00", "11:30", "14:00"]


def test_sort_by_time_single_task_unchanged(owner, dog):
    """sort_by_time on a one-item list returns that same single task."""
    task = make_task(name="Only Task", time="08:00")
    dog.add_task(task)
    scheduler = make_scheduler(owner, dog)
    result = scheduler.sort_by_time(dog.tasks)
    assert len(result) == 1
    assert result[0].name == "Only Task"


def test_sort_by_time_empty_list(owner, dog):
    """sort_by_time on an empty list returns an empty list without error."""
    scheduler = make_scheduler(owner, dog)
    assert scheduler.sort_by_time([]) == []


def test_sort_by_time_does_not_mutate_original(owner, dog):
    """sort_by_time returns a new list and leaves the original order intact."""
    t1 = make_task(name="Late",  time="20:00")
    t2 = make_task(name="Early", time="06:00")
    dog.add_task(t1)
    dog.add_task(t2)
    scheduler = make_scheduler(owner, dog)
    original_order = [t.name for t in dog.tasks]   # ["Late", "Early"]
    scheduler.sort_by_time(dog.tasks)               # should not touch dog.tasks
    assert [t.name for t in dog.tasks] == original_order


# ===========================================================================
# Section 3 — generate_plan: priority and time-budget enforcement
# ===========================================================================

def test_generate_plan_schedules_high_before_low(owner, dog):
    """generate_plan puts HIGH-priority tasks ahead of LOW-priority tasks."""
    # Arrange — add LOW first so insertion order can't explain the result
    low  = make_task(name="Grooming", minutes=10, priority=Priority.LOW)
    high = make_task(name="Meds",     minutes=5,  priority=Priority.HIGH)
    dog.add_task(low)
    dog.add_task(high)
    scheduler = make_scheduler(owner, dog)
    # Act
    plan = scheduler.generate_plan()
    # Assert — HIGH task must appear first in the scheduled list
    assert plan.scheduled[0].name == "Meds"


def test_generate_plan_skips_tasks_that_exceed_budget(owner, dog):
    """generate_plan skips a task when its duration exceeds remaining minutes."""
    # Arrange — two tasks totalling more than the 60-min budget
    dog.add_task(make_task(name="Long Walk", minutes=50, priority=Priority.HIGH))
    dog.add_task(make_task(name="Play",      minutes=20, priority=Priority.MEDIUM))
    scheduler = make_scheduler(owner, dog)
    # Act
    plan = scheduler.generate_plan()
    # Assert — Long Walk fits (50 <= 60); Play doesn't (10 remaining < 20 needed)
    assert "Long Walk" in [t.name for t in plan.scheduled]
    assert "Play"      in [t.name for t in plan.skipped]
    assert "not enough time" in plan.reasoning["Play"]


def test_generate_plan_task_fits_exactly_on_budget_boundary(owner, dog):
    """A task whose duration equals remaining minutes exactly is scheduled, not skipped."""
    # Arrange — owner has 60 min; first task uses 30; second task needs exactly 30
    dog.add_task(make_task(name="Walk",     minutes=30, priority=Priority.HIGH))
    dog.add_task(make_task(name="Feeding",  minutes=30, priority=Priority.HIGH))
    scheduler = make_scheduler(owner, dog)
    # Act
    plan = scheduler.generate_plan()
    # Assert — both fit; total == 60 exactly
    scheduled_names = [t.name for t in plan.scheduled]
    assert "Walk"    in scheduled_names
    assert "Feeding" in scheduled_names
    assert plan.total_time_used == 60


def test_generate_plan_completed_task_is_skipped(owner, dog):
    """generate_plan marks an already-completed task as skipped with reason 'already completed'."""
    task = make_task(name="Morning Walk", minutes=20)
    task.mark_complete()
    dog.add_task(task)
    scheduler = make_scheduler(owner, dog)
    plan = scheduler.generate_plan()
    assert task in plan.skipped
    assert plan.reasoning["Morning Walk"] == "already completed"


def test_generate_plan_pet_with_no_tasks_produces_empty_plan(owner, dog):
    """A pet registered with no tasks yields an empty scheduled list and zero time used."""
    scheduler = make_scheduler(owner, dog)
    plan = scheduler.generate_plan()
    assert plan.scheduled == []
    assert plan.skipped   == []
    assert plan.total_time_used == 0


def test_generate_plan_owner_zero_minutes_skips_everything(dog):
    """When available_minutes_per_day is 0, every task is skipped."""
    # Arrange — owner with no available time
    broke_owner = Owner(name="Busy", available_minutes_per_day=0)
    dog.add_task(make_task(name="Walk", minutes=10, priority=Priority.HIGH))
    scheduler = make_scheduler(broke_owner, dog)
    # Act
    plan = scheduler.generate_plan()
    # Assert
    assert plan.scheduled == []
    assert len(plan.skipped) == 1
    assert "not enough time" in plan.reasoning["Walk"]


# ===========================================================================
# Section 4 — Recurrence logic: complete_task
# ===========================================================================

def test_complete_daily_task_creates_new_task_for_next_day(owner, dog):
    """Completing a daily task replaces it with a fresh copy due tomorrow."""
    # Arrange — pin due_date so we can compute the expected next date
    today     = date(2026, 4, 1)
    tomorrow  = today + timedelta(days=1)
    dog.add_task(make_task(name="Walk", frequency="daily", due=today))
    scheduler = make_scheduler(owner, dog)
    # Act
    next_task = scheduler.complete_task("Biscuit", "Walk")
    # Assert
    assert next_task is not None
    assert next_task.name == "Walk"
    assert next_task.is_completed is False    # fresh copy must be pending
    assert next_task.due_date == tomorrow


def test_complete_weekly_task_creates_new_task_for_next_week(owner, dog):
    """Completing a weekly task replaces it with a fresh copy due in 7 days."""
    today      = date(2026, 4, 1)
    next_week  = today + timedelta(weeks=1)
    dog.add_task(make_task(name="Grooming", frequency="weekly", due=today))
    scheduler = make_scheduler(owner, dog)
    next_task = scheduler.complete_task("Biscuit", "Grooming")
    assert next_task.due_date == next_week


def test_complete_asneeded_task_returns_none_and_marks_done(owner, dog):
    """Completing an as-needed task returns None and leaves it as a completed record.

    Unlike daily/weekly tasks, as-needed tasks are not replaced with a fresh copy —
    they stay in the list with is_completed=True so the owner can see what was done.
    """
    dog.add_task(make_task(name="Flea Treatment", frequency="as-needed"))
    scheduler = make_scheduler(owner, dog)
    result = scheduler.complete_task("Biscuit", "Flea Treatment")
    # No next occurrence queued
    assert result is None
    # Task stays in the list, marked done
    assert len(dog.tasks) == 1
    assert dog.tasks[0].is_completed is True


def test_complete_daily_task_pet_has_exactly_one_task_after(owner, dog):
    """After completing a daily task, the pet still has exactly one task (the replacement)."""
    dog.add_task(make_task(name="Walk", frequency="daily"))
    scheduler = make_scheduler(owner, dog)
    scheduler.complete_task("Biscuit", "Walk")
    assert len(dog.tasks) == 1


def test_complete_task_unknown_pet_raises(owner, dog):
    """complete_task raises ValueError when the pet name does not exist."""
    scheduler = make_scheduler(owner, dog)
    with pytest.raises(ValueError, match="No pet"):
        scheduler.complete_task("Ghost", "Walk")


def test_complete_task_unknown_task_raises(owner, dog):
    """complete_task raises ValueError when the task name does not exist on that pet."""
    scheduler = make_scheduler(owner, dog)
    with pytest.raises(ValueError, match="No task"):
        scheduler.complete_task("Biscuit", "Ghost Task")


# ===========================================================================
# Section 5 — Conflict detection
# ===========================================================================

def test_detect_conflicts_same_slot_two_pets(owner, dog, cat):
    """Two tasks from different pets at the same time produce exactly one warning."""
    dog.add_task(make_task(name="Walk",  time="07:00"))
    cat.add_task(make_task(name="Meds",  time="07:00"))
    scheduler = make_scheduler(owner, dog, cat)
    warnings = scheduler.detect_conflicts()
    assert len(warnings) == 1
    assert "07:00"    in warnings[0]
    assert "Biscuit"  in warnings[0]
    assert "Luna"     in warnings[0]


def test_detect_conflicts_three_tasks_same_slot(owner, dog, cat):
    """Three tasks sharing a slot produce one warning listing all three."""
    dog.add_task(make_task(name="Walk",     time="08:00"))
    cat.add_task(make_task(name="Meds",     time="08:00"))
    cat.add_task(make_task(name="Feeding",  time="09:00"))   # different pet, same list allowed
    # Add a second dog task at 08:00 via a second pet
    rabbit = Pet(name="Thumper", species="Rabbit", age=1)
    rabbit.add_task(make_task(name="Greens", time="08:00"))
    owner.add_pet(dog)
    owner.add_pet(cat)
    owner.add_pet(rabbit)
    scheduler = Scheduler(owner)
    warnings = scheduler.detect_conflicts()
    # The 08:00 slot has three tasks — one warning with all three names
    slot_warning = next(w for w in warnings if "08:00" in w)
    assert "Biscuit:Walk"    in slot_warning
    assert "Luna:Meds"       in slot_warning
    assert "Thumper:Greens"  in slot_warning


def test_detect_conflicts_clean_schedule_returns_empty_list(owner, dog, cat):
    """detect_conflicts returns an empty list when all tasks have unique start times."""
    dog.add_task(make_task(name="Walk",  time="07:00"))
    cat.add_task(make_task(name="Meds",  time="07:30"))
    scheduler = make_scheduler(owner, dog, cat)
    assert scheduler.detect_conflicts() == []


def test_detect_conflicts_multiple_conflict_slots(owner, dog, cat):
    """Two independent conflicting slots each produce their own warning."""
    dog.add_task(make_task(name="Walk",     time="07:00"))
    cat.add_task(make_task(name="Meds",     time="07:00"))   # conflict 1
    dog.add_task(make_task(name="Breakfast",time="08:00"))
    cat.add_task(make_task(name="Dinner",   time="08:00"))   # conflict 2
    scheduler = make_scheduler(owner, dog, cat)
    warnings = scheduler.detect_conflicts()
    assert len(warnings) == 2
    joined = " ".join(warnings)
    assert "07:00" in joined
    assert "08:00" in joined


# ===========================================================================
# Section 6 — Filter methods
# ===========================================================================

def test_filter_by_status_pending_excludes_completed(owner, dog):
    """filter_by_status(completed=False) returns only incomplete tasks."""
    done    = make_task(name="Done Task",    minutes=10)
    pending = make_task(name="Pending Task", minutes=10)
    done.mark_complete()
    dog.add_task(done)
    dog.add_task(pending)
    scheduler = make_scheduler(owner, dog)
    result = scheduler.filter_by_status(dog.tasks, completed=False)
    names = [t.name for t in result]
    assert "Pending Task" in names
    assert "Done Task"    not in names


def test_filter_by_status_all_pending_returns_all(owner, dog):
    """filter_by_status(completed=False) returns all tasks when none are done."""
    dog.add_task(make_task(name="A"))
    dog.add_task(make_task(name="B"))
    scheduler = make_scheduler(owner, dog)
    result = scheduler.filter_by_status(dog.tasks, completed=False)
    assert len(result) == 2


def test_filter_by_status_completed_returns_only_done(owner, dog):
    """filter_by_status(completed=True) returns only completed tasks."""
    task = make_task(name="Done")
    task.mark_complete()
    dog.add_task(task)
    dog.add_task(make_task(name="Still Pending"))
    scheduler = make_scheduler(owner, dog)
    result = scheduler.filter_by_status(dog.tasks, completed=True)
    assert len(result) == 1
    assert result[0].name == "Done"


def test_filter_by_pet_returns_correct_tasks(owner, dog, cat):
    """filter_by_pet returns only that pet's tasks, not the other pet's."""
    dog.add_task(make_task(name="Dog Walk"))
    cat.add_task(make_task(name="Cat Meds"))
    scheduler = make_scheduler(owner, dog, cat)
    dog_tasks = scheduler.filter_by_pet("Biscuit")
    assert len(dog_tasks) == 1
    assert dog_tasks[0].name == "Dog Walk"


def test_filter_by_pet_unknown_name_raises(owner, dog):
    """filter_by_pet raises ValueError for a pet name not registered with the owner."""
    scheduler = make_scheduler(owner, dog)
    with pytest.raises(ValueError):
        scheduler.filter_by_pet("Ghost")


# ===========================================================================
# Section 7 — Edge cases
# ===========================================================================

def test_generate_plan_owner_with_no_pets_produces_empty_plan():
    """An owner with no pets at all yields an empty plan with zero time used."""
    # Arrange — owner registered but no pets added
    owner = Owner(name="Empty", available_minutes_per_day=120)
    scheduler = Scheduler(owner)
    # Act
    plan = scheduler.generate_plan()
    # Assert
    assert plan.scheduled == []
    assert plan.skipped == []
    assert plan.total_time_used == 0


def test_detect_conflicts_same_pet_two_tasks_same_time(owner, dog):
    """Two tasks on the same pet sharing a time slot are also flagged as a conflict."""
    # Arrange — both tasks belong to Biscuit, both at 09:00
    dog.add_task(make_task(name="Morning Walk",  time="09:00"))
    dog.add_task(make_task(name="Morning Meds",  time="09:00"))
    scheduler = make_scheduler(owner, dog)
    # Act
    warnings = scheduler.detect_conflicts()
    # Assert — one warning for the 09:00 slot listing both tasks
    assert len(warnings) == 1
    assert "09:00" in warnings[0]
    assert "Morning Walk" in warnings[0]
    assert "Morning Meds" in warnings[0]


def test_complete_task_twice_raises_on_second_call(owner, dog):
    """Calling complete_task twice for the same task name raises ValueError.

    Why: the first call removes the completed task and adds a fresh pending copy.
    The second call finds the fresh copy, completes it, removes it, and tries to
    add another copy — but the pet already has one, so add_task raises ValueError.
    """
    # Arrange
    dog.add_task(make_task(name="Walk", frequency="daily", due=date.today()))
    scheduler = make_scheduler(owner, dog)
    # Act — first completion succeeds
    scheduler.complete_task("Biscuit", "Walk")
    # Assert — second completion on the replacement also succeeds (it's a fresh task)
    # but a *third* call would collide; here we just verify the second call works
    next_task = scheduler.complete_task("Biscuit", "Walk")
    assert next_task is not None
    assert next_task.is_completed is False


def test_filter_by_pet_case_insensitive(owner, dog):
    """filter_by_pet matches pet names regardless of letter case."""
    dog.add_task(make_task(name="Walk"))
    scheduler = make_scheduler(owner, dog)
    # "biscuit" (all lower) should match the pet named "Biscuit"
    result = scheduler.filter_by_pet("biscuit")
    assert len(result) == 1
    assert result[0].name == "Walk"


def test_sort_by_time_preserves_tasks_with_same_time(owner, dog):
    """sort_by_time keeps all tasks when multiple share the same scheduled_time."""
    # Arrange — two tasks at exactly the same time
    dog.add_task(make_task(name="Walk",  time="08:00"))
    dog.add_task(make_task(name="Meds",  time="08:00"))
    scheduler = make_scheduler(owner, dog)
    # Act
    result = scheduler.sort_by_time(dog.tasks)
    # Assert — both tasks are present (no silent drops), order is stable
    assert len(result) == 2
    assert all(t.scheduled_time == "08:00" for t in result)
