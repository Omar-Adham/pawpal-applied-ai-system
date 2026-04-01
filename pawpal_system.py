from dataclasses import dataclass, field
from enum import Enum


class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class Owner:
    name: str
    available_minutes_per_day: int


@dataclass
class Pet:
    name: str
    species: str
    age: int
    special_needs: list[str] = field(default_factory=list)


@dataclass
class Task:
    name: str
    category: str          # e.g. "walk", "feed", "meds", "grooming", "enrichment"
    duration_minutes: int
    priority: Priority
    is_completed: bool = False

    def mark_complete(self) -> None:
        pass

    def __repr__(self) -> str:
        pass


@dataclass
class DailyPlan:
    owner: Owner = None
    pet: Pet = None
    scheduled: list[Task] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    total_time_used: int = 0
    reasoning: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        pass


class Scheduler:
    def __init__(self, owner: Owner, pet: Pet) -> None:
        self.owner = owner
        self.pet = pet
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        # Prevent duplicate task names
        if any(t.name == task.name for t in self.tasks):
            raise ValueError(f"A task named '{task.name}' already exists.")
        self.tasks.append(task)

    def remove_task(self, name: str) -> None:
        # Removes the first task matching the given name
        for i, task in enumerate(self.tasks):
            if task.name == name:
                self.tasks.pop(i)
                return
        raise ValueError(f"No task named '{name}' found.")

    def generate_plan(self) -> DailyPlan:
        return DailyPlan(owner=self.owner, pet=self.pet)
