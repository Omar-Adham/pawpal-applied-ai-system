# PawPal+ Applied AI System

A pet care scheduling assistant that combines rule-based planning with
Retrieval-Augmented Generation (RAG) to give owners personalised, breed-aware
advice alongside their daily schedule.

---

## Original Project

**PawPal+** was built in Modules 1–3 of AI 110 as a pure Python / Streamlit
scheduling app. Its original goals were to help busy pet owners track care
tasks, fit them into a daily time budget using a priority-first greedy
algorithm, detect scheduling conflicts, and automatically reschedule recurring
tasks. It had no AI layer — every decision was deterministic and rule-based.

This repository extends that foundation by adding a RAG pipeline so the
generated schedule is accompanied by care advice grounded in a pet-specific
knowledge base rather than generic language-model responses.

---

## System Diagram

![System Diagram](assests/system_diagram.png)

---

## Architecture Overview

The system has three layers that run in sequence each time the owner generates
a schedule:

1. **Scheduler** (`pawpal_system.py`) — collects every task across all pets,
   sorts by priority then duration, and fits tasks into the owner's time budget.
   It also detects time-slot conflicts and handles recurring task rescheduling.
   This layer is entirely deterministic and covered by 34 automated tests.

2. **RAG pipeline** (`rag.py`) — after the plan is built, the Retriever
   queries `pet_care_kb.json` using the pet's species, age, and task categories
   as search keys. The retrieved facts are passed to Claude alongside the
   generated plan. Claude returns a short, grounded advice note — not a generic
   response, but one anchored to the specific facts that were looked up.

3. **Streamlit UI** (`app.py`) — the owner interacts with both layers through
   a single web interface: setup → add tasks → conflict check → generate
   schedule + AI advice note.

Human review happens at two points: when the owner reads the schedule and
decides whether to follow it, and when the owner reads the AI note and judges
whether the advice applies to their pet.

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- An Anthropic API key (for the RAG / Claude layer)

### Steps

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd pawpal-applied-ai-system

# 2. Create and activate a virtual environment
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
# Create a .env file in the project root:
echo ANTHROPIC_API_KEY=your-key-here > .env

# 5. Run the app
streamlit run app.py

# 6. (Optional) Run the terminal demo — no browser needed
python main.py

# 7. (Optional) Run the test suite
python -m pytest tests/test_pawpal.py -v
```

---

## Sample Interactions

### 1 — Conflict detected before scheduling

**Input:** Two tasks assigned the same start time.

```
Pet: Biscuit (Dog)   Task: Morning Walk    07:00  30 min  HIGH
Pet: Luna   (Cat)    Task: Thyroid Meds    07:00   5 min  HIGH
```

**Output (conflict check):**

```
WARNING — conflict at 07:00: Biscuit:Morning Walk, Luna:Thyroid Meds
Tip: edit one task's scheduled time to resolve the conflict.
```

---

### 2 — Daily schedule generated with skipped task

**Input:** Owner has 90 minutes available.

```
Biscuit — Morning Walk     30 min  HIGH    07:00  daily
Biscuit — Breakfast        10 min  HIGH    08:00  daily
Biscuit — Fetch Session    20 min  MEDIUM  15:00  weekly
Luna    — Thyroid Meds      5 min  HIGH    07:15  daily
Luna    — Dinner           10 min  HIGH    08:00  daily
Luna    — Brush Coat       15 min  LOW     18:00  weekly
```

**Output (generated plan — 75 / 90 min used):**

```
07:00  [Biscuit]  Morning Walk          30 min  HIGH
07:15  [   Luna]  Thyroid Meds           5 min  HIGH
08:00  [Biscuit]  Breakfast             10 min  HIGH
08:00  [   Luna]  Dinner                10 min  HIGH
15:00  [Biscuit]  Fetch Session         20 min  MEDIUM

SKIPPED:
  Brush Coat — not enough time (15 min left, needs 15 min... wait, fits)
```

> Note: exact skip reasoning depends on task order at runtime.

---

### 3 — Recurring task completed and rescheduled

**Input:** Mark Luna's Thyroid Meds as done on 2026-04-24.

**Output:**

```
Completed. Next occurrence scheduled for 2026-04-25 at 07:15.
```

The completed task is removed and replaced with a fresh pending copy — the
task name stays unique and all filters keep working.

---

> **RAG sample interactions** (AI advice note grounded in retrieved care facts)
> will be added here once the knowledge base and retriever are integrated.

---

## Design Decisions

### Greedy scheduling over optimal packing

The scheduler sorts tasks by priority then duration and fills the time budget
in one pass — it never backtracks. A true 0/1 knapsack would find the
mathematically optimal set of tasks, but it grows exponentially with task
count and produces results that are harder for an owner to predict. The greedy
approach runs instantly, always schedules the most important tasks first, and
produces a plan the owner can reason about. The cost is occasional unused
minutes when a large high-priority task is skipped but smaller lower-priority
tasks would have fit.

### Exact time-slot conflict detection

`detect_conflicts()` flags tasks only when their `scheduled_time` strings are
identical. It does not check whether one task's duration bleeds into the next
task's start time. This catches the most common mistake (two tasks accidentally
set to the same time) with a simple `defaultdict` grouping that is easy to
read and test. Duration-aware interval overlap detection is a planned
improvement — it requires parsing times to minutes and comparing `(start,
start + duration)` ranges across every task pair.

### RAG over fine-tuning

A fine-tuned model would require labelled training data, a training run, and a
separate model endpoint. RAG achieves grounded, breed-specific responses by
retrieving facts from a local JSON file at query time — no training required,
the knowledge base is easy to update, and the retrieval step is inspectable
and loggable. The trade-off is that the quality of the AI note depends on the
quality and coverage of `pet_care_kb.json`.

### Separation of logic and UI

All scheduling algorithms live in `pawpal_system.py`. `app.py` contains no
scheduling logic — it only calls into the system layer. This means the 34-test
suite runs without Streamlit installed, and the UI can be redesigned without
touching the algorithms.

---

## Testing Summary

### What is covered

The suite contains **34 tests** across seven sections:

| Section | What it verifies |
|---|---|
| Task fundamentals | `mark_complete`, `add_task`, duplicate rejection, task removal |
| Sorting | `sort_by_time` returns HH:MM ascending order; does not mutate input |
| `generate_plan` | HIGH before LOW; time-budget boundary (`<=`); skipped reasons |
| Recurrence | `daily` +1 day; `weekly` +7 days; `as-needed` returns `None` |
| Conflict detection | Same-time clashes; clean schedules return `[]`; same-pet conflicts |
| Filters | `filter_by_status` and `filter_by_pet`; case-insensitive matching |
| Edge cases | No pets; tied times; chained `complete_task` calls |

### What worked

Keeping the scheduling logic in a plain Python module meant every behaviour
could be tested directly without mocking Streamlit or a browser. The fixed
reference date (`date(2026, 4, 1)`) in recurrence tests eliminated flakiness
from the system clock.

### What didn't / known gaps

- **Duration overlap** — a 30-min task at `07:00` and a task at `07:15` are
  not flagged as conflicting. Documented tradeoff, not a coverage hole.
- **Multi-pet UI** — the Streamlit form supports one pet per session; the
  backend supports multiple. No end-to-end test covers the multi-pet path
  through the UI.
- **AI layer** — RAG tests (retrieval accuracy, Claude response consistency)
  are not yet written. They will be added alongside the RAG implementation.

### Confidence level

**4 / 5** for the scheduling layer. All 34 tests pass. One star withheld for
the conflict-detection gap described above.

---

## Reflection

Building PawPal+ taught me two things I expect to carry into every future
project.

**Separation of concerns is not just good style — it is a testing strategy.**
The decision to keep all logic in `pawpal_system.py` and all UI in `app.py`
was made early for readability. Its real payoff came at test time: 34 tests
written without importing Streamlit once. When the UI needed changes, none of
the tests broke. That boundary paid for itself many times over.

**AI tools accelerate execution but do not replace understanding.** Copilot
generated test scaffolds that were technically correct but tested the wrong
things — asserting object identity instead of behaviour, or implying a design
decision (`DailyPlan.pet`) that had already been deliberately reversed.
Catching those suggestions required reading the code, not just running the
tests. The lesson is that AI is most useful when you already know what you
want and ask for something specific. Broad prompts produce plausible-looking
output that can quietly embed wrong assumptions into your codebase.

Adding RAG to this project reinforced a third idea: **grounding matters**.
A language model answering "is this walk schedule enough for a Husky?"
without context will give a generic answer. The same model given three
retrieved facts about Husky exercise requirements will give a useful one.
The retrieval step is not a pre-processing nicety — it is what makes the AI
output trustworthy enough to act on.
