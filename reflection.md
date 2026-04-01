# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

1. **Set up a pet profile** — The user enters basic information about themselves and their pet (owner name, pet name, pet type, and available time per day). This gives the scheduler the constraints it needs to build a realistic plan.

2. **Add and manage care tasks** — The user creates tasks such as walks, feeding, medication, grooming, or enrichment. Each task has at minimum a name, an estimated duration, and a priority level. The user can also edit or remove tasks as the pet's needs change.

3. **Generate and review a daily schedule** — The user asks the app to produce a daily care plan. The scheduler fits tasks into the owner's available time window, ordered by priority. The app displays the resulting plan and explains why tasks were included, deferred, or skipped, so the owner understands the reasoning.

**UML Class Diagram (Mermaid.js):**

```mermaid
classDiagram
    class Owner {
        +String name
        +int available_minutes_per_day
    }

    class Pet {
        +String name
        +String species
        +int age
        +List~String~ special_needs
    }

    class Task {
        +String name
        +String category
        +int duration_minutes
        +Priority priority
        +bool is_completed
        +mark_complete()
        +__repr__() String
    }

    class Priority {
        <<enumeration>>
        HIGH
        MEDIUM
        LOW
    }

    class Scheduler {
        +Pet pet
        +Owner owner
        +List~Task~ tasks
        +add_task(task: Task)
        +remove_task(name: String)
        +generate_plan() DailyPlan
    }

    class DailyPlan {
        +Owner owner
        +Pet pet
        +List~Task~ scheduled
        +List~Task~ skipped
        +int total_time_used
        +Dict reasoning
        +summary() String
    }

    Scheduler --> Owner : has
    Scheduler --> Pet : manages care for
    Scheduler --> Task : holds list of
    Scheduler --> DailyPlan : produces
    Task --> Priority : uses
    DailyPlan --> Owner : references
    DailyPlan --> Pet : references
```

The initial design has five classes organized around a central `Scheduler` that coordinates all the other objects.

- **`Owner`** — a data-only class that holds the owner's name and how many minutes per day they have available for pet care. It represents the time constraint the scheduler must respect.

- **`Pet`** — a data-only class that stores the pet's name, species, age, and any special needs (e.g. "needs medication twice daily"). It gives the scheduler context about who is being cared for.

- **`Task`** — represents a single care activity. It holds the task name, category (walk, feed, meds, grooming, enrichment), estimated duration in minutes, priority level (high/medium/low), and whether it has been completed. It can mark itself complete and produce a readable string description.

- **`Scheduler`** — the central coordinator. It owns an `Owner`, a `Pet`, and a list of `Task` objects. Its job is to accept new tasks, remove tasks by name, and run `generate_plan()` which applies the scheduling logic and returns a `DailyPlan`.

- **`DailyPlan`** — the output of scheduling. It holds two lists (scheduled tasks and skipped tasks), the total time used, and a reasoning dictionary that maps each skipped task to the reason it was left out. Its `summary()` method produces a human-readable explanation of the plan.

**b. Design changes**

After reviewing the skeleton, four changes were made based on identified gaps:

1. **Added a `Priority` enum instead of a plain string.**
   The original design used `priority: str`, which meant values like `"high"`, `"High"`, and `"urgent"` were all silently valid. When `generate_plan()` sorts tasks by priority it needs consistent, comparable values. Replacing the string with a `Priority(Enum)` with members `HIGH = 1`, `MEDIUM = 2`, `LOW = 3` makes sorting unambiguous and catches bad values at assignment time rather than silently at runtime.

2. **Added `owner` and `pet` fields to `DailyPlan`.**
   `DailyPlan` had no reference to who the plan was for. Without this, `summary()` could not include context like the pet's name or the owner's available time. Passing `owner` and `pet` into `DailyPlan` at construction time gives the output object everything it needs to produce a complete, readable summary.

3. **Gave `generate_plan()` a safe placeholder return.**
   The stub returned `None` implicitly, meaning any code that called `plan.scheduled` before the method was implemented would raise an `AttributeError`. Returning `DailyPlan(owner=self.owner, pet=self.pet)` makes the skeleton safely runnable end-to-end even before the scheduling logic is filled in.

4. **Implemented duplicate-checking in `add_task()` and first-match removal in `remove_task()`.**
   Without a uniqueness check, the same task name could be added twice, making removal ambiguous. `add_task()` now raises a `ValueError` if a task with that name already exists. `remove_task()` removes the first match and raises `ValueError` if no match is found, making the behavior explicit rather than silently doing nothing.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
