from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum


class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class Task:
    """A single pet care activity.

    Attributes:
        name:             Human-readable label, e.g. "Morning Walk".
        category:         Broad type — "walk", "feed", "meds", "grooming", "enrichment".
        duration_minutes: How long the activity takes; used for time-budget fitting.
        priority:         Priority.HIGH / MEDIUM / LOW — drives scheduling order.
        frequency:        How often the task recurs: "daily", "weekly", or "as-needed".
                          complete_task() uses this to calculate the next due_date.
        scheduled_time:   "HH:MM" string for the time of day this task should start.
                          Defaults to "09:00"; used by sort_by_time() and detect_conflicts().
        due_date:         The calendar date this occurrence is due, set to today by default.
                          complete_task() advances it by timedelta(days=1) or timedelta(weeks=1).
        is_completed:     True once mark_complete() has been called for this occurrence.
    """
    name: str
    category: str           # "walk", "feed", "meds", "grooming", "enrichment"
    duration_minutes: int
    priority: Priority
    frequency: str = "daily"                          # "daily", "weekly", "as-needed"
    scheduled_time: str = "09:00"                     # "HH:MM" — time of day
    due_date: date = field(default_factory=date.today) # date this occurrence is due
    is_completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done for the current period."""
        self.is_completed = True

    def __repr__(self) -> str:
        status = "[x]" if self.is_completed else "[ ]"
        return (
            f"{status} {self.scheduled_time}  {self.name} "
            f"({self.duration_minutes}min, {self.priority.name}, "
            f"{self.frequency}, due {self.due_date})"
        )


@dataclass
class Pet:
    """A pet with its own list of care tasks."""
    name: str
    species: str
    age: int
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet, rejecting duplicates by name."""
        if any(t.name == task.name for t in self.tasks):
            raise ValueError(f"Task '{task.name}' already exists for {self.name}.")
        self.tasks.append(task)

    def remove_task(self, name: str) -> None:
        """Remove the first task matching the given name."""
        for i, task in enumerate(self.tasks):
            if task.name == name:
                self.tasks.pop(i)
                return
        raise ValueError(f"No task named '{name}' found for {self.name}.")

    def get_tasks(self) -> list[Task]:
        """Return a copy of this pet's task list."""
        return list(self.tasks)


@dataclass
class Owner:
    """A pet owner who may have multiple pets."""
    name: str
    available_minutes_per_day: int
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner, rejecting duplicates by name."""
        if any(p.name == pet.name for p in self.pets):
            raise ValueError(f"A pet named '{pet.name}' is already registered.")
        self.pets.append(pet)

    def remove_pet(self, name: str) -> None:
        """Remove the pet with the given name."""
        for i, pet in enumerate(self.pets):
            if pet.name == name:
                self.pets.pop(i)
                return
        raise ValueError(f"No pet named '{name}' found.")

    def get_all_tasks(self) -> list[Task]:
        """Collect and return every task across all pets."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks


@dataclass
class DailyPlan:
    """The output of a scheduling run."""
    owner: Owner = None
    scheduled: list[Task] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    total_time_used: int = 0
    reasoning: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        """Return a human-readable description of the plan and its reasoning."""
        owner_name = self.owner.name if self.owner else "Unknown"
        available = self.owner.available_minutes_per_day if self.owner else 0
        lines = [
            f"Daily Plan for {owner_name}  "
            f"({self.total_time_used}/{available} min used)",
            "",
        ]

        if self.scheduled:
            lines.append("Scheduled:")
            for task in self.scheduled:
                lines.append(f"  {task!r}")

        if self.skipped:
            lines.append("")
            lines.append("Skipped:")
            for task in self.skipped:
                reason = self.reasoning.get(task.name, "unknown reason")
                lines.append(f"  {task!r}  — {reason}")

        return "\n".join(lines)


class Scheduler:
    """Retrieves tasks from the Owner's pets and builds a prioritized daily plan."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Ask the Owner for every task across all its pets."""
        return self.owner.get_all_tasks()

    def add_task_to_pet(self, pet_name: str, task: Task) -> None:
        """Convenience method: find a pet by name and add a task to it."""
        for pet in self.owner.pets:
            if pet.name == pet_name:
                pet.add_task(task)
                return
        raise ValueError(f"No pet named '{pet_name}' found.")

    def remove_task_from_pet(self, pet_name: str, task_name: str) -> None:
        """Convenience method: find a pet by name and remove a task from it."""
        for pet in self.owner.pets:
            if pet.name == pet_name:
                pet.remove_task(task_name)
                return
        raise ValueError(f"No pet named '{pet_name}' found.")

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted ascending by their scheduled_time ("HH:MM") string.

        Sorting "HH:MM" strings lexicographically works correctly because the
        format has fixed-width zero-padded fields — "07:30" < "09:00" < "14:15".
        Using a lambda as the key extracts the time string for each Task object
        so sorted() can compare them.
        """
        return sorted(tasks, key=lambda t: t.scheduled_time)

    def filter_by_status(self, tasks: list[Task], completed: bool) -> list[Task]:
        """Return only tasks whose is_completed flag matches *completed*.

        Pass completed=False to get the pending work list;
        pass completed=True to review what is already done.
        """
        return [t for t in tasks if t.is_completed == completed]

    def filter_by_pet(self, pet_name: str) -> list[Task]:
        """Return all tasks belonging to the pet with the given name.

        Raises ValueError if no pet with that name is registered under this owner.
        """
        for pet in self.owner.pets:
            if pet.name.lower() == pet_name.lower():
                return list(pet.tasks)
        raise ValueError(f"No pet named '{pet_name}' found.")

    def complete_task(self, pet_name: str, task_name: str) -> "Task | None":
        """Mark a task complete and automatically queue the next occurrence.

        For recurring tasks, timedelta shifts the due_date forward:
          - "daily"     → due_date + timedelta(days=1)
          - "weekly"    → due_date + timedelta(weeks=1)
          - "as-needed" → no new task; returns None

        The completed task is removed from the pet's list and replaced with a
        fresh instance so the task name stays unique and the list only ever
        holds one entry per task — either pending or the next scheduled copy.

        Returns the newly-created Task if one was queued, else None.
        """
        # Locate the pet — next() returns the first match or None
        target_pet = next(
            (p for p in self.owner.pets if p.name.lower() == pet_name.lower()), None
        )
        if target_pet is None:
            raise ValueError(f"No pet named '{pet_name}' found.")

        # Locate the task on that pet
        target_task = next(
            (t for t in target_pet.tasks if t.name == task_name), None
        )
        if target_task is None:
            raise ValueError(f"No task named '{task_name}' found for {pet_name}.")

        target_task.mark_complete()

        # Determine next due_date using timedelta
        if target_task.frequency == "daily":
            next_due = target_task.due_date + timedelta(days=1)
        elif target_task.frequency == "weekly":
            next_due = target_task.due_date + timedelta(weeks=1)
        else:
            # "as-needed" tasks are not automatically rescheduled
            return None

        # Replace the completed task with a fresh pending copy for the next cycle
        target_pet.remove_task(task_name)
        next_task = Task(
            name=target_task.name,
            category=target_task.category,
            duration_minutes=target_task.duration_minutes,
            priority=target_task.priority,
            frequency=target_task.frequency,
            scheduled_time=target_task.scheduled_time,
            due_date=next_due,
        )
        target_pet.add_task(next_task)
        return next_task

    def detect_conflicts(self) -> list[str]:
        """Return warning strings for every scheduled_time slot claimed by more than one task.

        Strategy: group all tasks across every pet by their scheduled_time using a
        defaultdict(list). Any slot with two or more entries is a conflict.
        Returns an empty list when the schedule is clean.

        This is lightweight — it never raises an exception, so callers can print
        the warnings and keep running rather than crashing on a bad schedule.
        """
        slots: dict[str, list[str]] = defaultdict(list)
        for pet in self.owner.pets:
            for task in pet.tasks:
                slots[task.scheduled_time].append(f"{pet.name}:{task.name}")

        warnings = []
        for time_slot, entries in slots.items():
            if len(entries) > 1:
                clashes = ", ".join(entries)
                warnings.append(f"WARNING - conflict at {time_slot}: {clashes}")
        return warnings

    def generate_plan(self) -> DailyPlan:
        """Build and return a DailyPlan for the owner's available time today.

        Algorithm (greedy priority-first):
          1. Collect every task across all pets via Owner.get_all_tasks().
          2. Sort by (priority.value, duration_minutes) so HIGH-priority tasks
             are scheduled first; shorter tasks break ties within the same priority.
          3. Walk the sorted list and fit each task into the remaining time budget.
             Already-completed tasks are recorded as skipped with reason "already completed".
             Tasks that exceed the remaining budget are skipped with a reason explaining
             how many minutes were left vs. how many were needed.

        The greedy approach is O(n log n) and gives predictable, human-readable results,
        at the cost of occasionally leaving unused minutes when a large high-priority task
        does not fit but smaller lower-priority tasks would have. See reflection.md Tradeoff 1.
        """
        all_tasks = self.get_all_tasks()
        sorted_tasks = sorted(
            all_tasks,
            key=lambda t: (t.priority.value, t.duration_minutes),
        )

        plan = DailyPlan(owner=self.owner)
        time_remaining = self.owner.available_minutes_per_day

        for task in sorted_tasks:
            if task.is_completed:
                plan.reasoning[task.name] = "already completed"
                plan.skipped.append(task)
            elif task.duration_minutes <= time_remaining:
                plan.scheduled.append(task)
                plan.total_time_used += task.duration_minutes
                time_remaining -= task.duration_minutes
            else:
                plan.reasoning[task.name] = (
                    f"not enough time "
                    f"({time_remaining} min left, needs {task.duration_minutes} min)"
                )
                plan.skipped.append(task)

        return plan
