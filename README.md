# PawPal+ (Module 2 Project)

**PawPal+** is a Python-backed Streamlit app that helps busy pet owners build a realistic daily care plan for their pets. The owner enters how much time they have, adds tasks for each pet, and the scheduler prioritises, sorts, and fits those tasks into a time-budgeted plan — flagging conflicts and automatically rescheduling recurring tasks.

## Features

### Priority-based daily schedule
The scheduler uses a **greedy priority-first algorithm** to build each day's plan. Tasks are sorted by `Priority` (HIGH → MEDIUM → LOW) and, within the same priority, by duration (shortest first to maximise fit). Each task is accepted or skipped based on the owner's remaining time budget, and every decision is recorded with a plain-English reason so the owner always understands why a task was left out.

### Chronological time sorting
`Scheduler.sort_by_time()` orders any task list by `scheduled_time` using lexicographic comparison on zero-padded `"HH:MM"` strings — no date-time parsing required. Every view in the app (task list, generated schedule) displays tasks in the order the owner will actually do them.

### Conflict warnings
`Scheduler.detect_conflicts()` scans all pets' tasks and flags any `scheduled_time` slot claimed by more than one task. It uses a `defaultdict(list)` to group tasks by start time and returns a list of warning strings — one per conflicting slot — without raising exceptions, so the UI can display warnings and keep running. The app surfaces these as `st.error` banners with expandable detail and a tip on how to fix each conflict.

### Automatic daily recurrence
`Scheduler.complete_task()` marks a task done and immediately queues the next occurrence using Python's `timedelta`:

| Frequency | Next due date |
|-----------|--------------|
| `"daily"` | `due_date + 1 day` |
| `"weekly"` | `due_date + 7 days` |
| `"as-needed"` | not rescheduled — stays in the list as a completed record |

The completed task is removed and replaced with a fresh pending copy so the task name stays unique and all filters remain consistent.

### Per-pet and status filtering
Two read-only filter methods let the UI slice the task list without mutating it:

- `filter_by_pet(pet_name)` — returns only that pet's tasks (case-insensitive match)
- `filter_by_status(tasks, completed)` — returns pending (`False`) or completed (`True`) tasks

### Duplicate and integrity guards
`Pet.add_task()` rejects a task whose name already exists on that pet. `Owner.add_pet()` rejects a pet whose name is already registered. Both raise `ValueError` with a descriptive message that the UI catches and displays via `st.error`.

---

## 📸 Demo

<a href="/course_images/ai110/pawpal_screenshot01.png" target="_blank"><img src='/course_images/ai110/pawpal_screenshot01.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="/course_images/ai110/pawpal_screenshot02.png" target="_blank"><img src='/course_images/ai110/pawpal_screenshot02.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="/course_images/ai110/pawpal_screenshot03.png" target="_blank"><img src='/course_images/ai110/pawpal_screenshot03.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

---

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

## Architecture

The scheduling logic lives entirely in [`pawpal_system.py`](pawpal_system.py). The Streamlit UI in [`app.py`](app.py) calls into it — it contains no scheduling logic of its own. The class structure is documented in [`uml_final.png`](uml_final.png) and [`reflection.md`](reflection.md).

```
Owner  1 ──*  Pet  1 ──*  Task  ──►  Priority (enum)
  ▲                               
  │  coordinates                  
Scheduler  ──(produces)──►  DailyPlan
```

## Smarter Scheduling

Phase 3 extended the core `Scheduler` class in `pawpal_system.py` with four algorithmic improvements beyond the original priority-based greedy fill.

### Sort by time

`Scheduler.sort_by_time(tasks)` orders any list of tasks chronologically using
Python's `sorted()` with a lambda key: `key=lambda t: t.scheduled_time`.
Because `scheduled_time` is stored as a zero-padded `"HH:MM"` string,
lexicographic comparison gives the correct time order with no extra parsing.

### Filter by pet and status

Two filter methods make it easy to slice the task list:

- `filter_by_pet(pet_name)` — returns only the tasks belonging to a named pet,
  enabling per-pet schedule views in the UI.
- `filter_by_status(tasks, completed)` — returns pending tasks (`completed=False`)
  or already-done tasks (`completed=True`), driving the daily checklist view.

### Recurring task automation

`Scheduler.complete_task(pet_name, task_name)` marks a task done and
automatically queues the next occurrence using Python's `timedelta`:

| Frequency | Next due date |
|---|---|
| `"daily"` | `due_date + timedelta(days=1)` |
| `"weekly"` | `due_date + timedelta(weeks=1)` |
| `"as-needed"` | not rescheduled — returns `None` |

The completed task is removed and replaced with a fresh pending copy so the
task name stays unique and all filters keep working without special cases.

### Conflict detection

`Scheduler.detect_conflicts()` scans every pet's tasks and reports any
`scheduled_time` slot claimed by more than one task. It uses a
`defaultdict(list)` to group tasks by start time, then returns a plain list
of warning strings — never raising an exception — so the caller can display
warnings and keep running. An empty list means the schedule is clean.

> **Current limitation:** conflicts are detected by exact start-time match only.
> A 30-minute task starting at `07:00` that bleeds into a task at `07:15`
> will not be flagged. See `reflection.md` Tradeoff 2 for details.

## Testing PawPal+

### Run the test suite

```bash
python -m pytest tests/test_pawpal.py -v
```

### What the tests cover

The suite contains **34 tests** across seven sections:

| Section | What it verifies |
|---------|-----------------|
| Task fundamentals | `mark_complete`, `add_task`, duplicate rejection, missing-task removal |
| Sorting correctness | `sort_by_time` returns tasks in `HH:MM` ascending order, handles empty lists, does not mutate the original |
| `generate_plan` | HIGH-priority tasks are scheduled before LOW; tasks that exceed the time budget are skipped with a reason; boundary case where task duration exactly equals remaining time |
| Recurrence logic | Completing a `daily` task creates a new task due tomorrow; `weekly` advances by 7 days; `as-needed` returns `None` and stays marked done |
| Conflict detection | Overlapping `scheduled_time` slots produce warning strings; clean schedules return `[]`; same-pet conflicts are also flagged |
| Filter methods | `filter_by_status` and `filter_by_pet` return correct subsets; case-insensitive pet name matching works |
| Edge cases | Owner with no pets, tied scheduled times, chained `complete_task` calls |

### Confidence level

**4 / 5 stars**

All 34 tests pass and cover both happy paths and the most important edge cases.
One star is withheld because conflict detection uses exact start-time matching only — a 30-minute task at `07:00` and a task at `07:15` will not be flagged as overlapping (see `reflection.md` Tradeoff 2).
That gap is a known limitation of the current algorithm, not a test coverage hole.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
