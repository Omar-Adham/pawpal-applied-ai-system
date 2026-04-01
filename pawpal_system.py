from dataclasses import dataclass, field


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
    priority: str          # "high", "medium", or "low"
    is_completed: bool = False

    def mark_complete(self) -> None:
        pass

    def __repr__(self) -> str:
        pass


@dataclass
class DailyPlan:
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

    def add_task(self, _task: Task) -> None:
        pass

    def remove_task(self, _name: str) -> None:
        pass

    def generate_plan(self) -> DailyPlan:
        pass
