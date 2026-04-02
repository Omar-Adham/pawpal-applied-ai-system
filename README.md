# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

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
