from dataclasses import dataclass, field
from enum import Enum


class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class Task:
    """A single pet care activity."""
    name: str
    category: str           # "walk", "feed", "meds", "grooming", "enrichment"
    duration_minutes: int
    priority: Priority
    frequency: str = "daily"  # "daily", "weekly", "as-needed"
    is_completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done for the current period."""
        self.is_completed = True

    def __repr__(self) -> str:
        status = "✓" if self.is_completed else "○"
        return (
            f"[{status}] {self.name} "
            f"({self.duration_minutes}min, {self.priority.name}, {self.frequency})"
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

    def generate_plan(self) -> DailyPlan:
        """
        Build a DailyPlan by:
        1. Collecting all tasks from all pets via the Owner.
        2. Sorting by priority (HIGH first), then duration (shorter first as tiebreaker).
        3. Greedily fitting tasks into the owner's available time budget.
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
