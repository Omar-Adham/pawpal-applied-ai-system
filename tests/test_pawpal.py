import pytest
from pawpal_system import Pet, Task, Priority


# --- Fixtures ---

@pytest.fixture
def sample_task():
    return Task(
        name="Morning Walk",
        category="walk",
        duration_minutes=30,
        priority=Priority.HIGH,
    )

@pytest.fixture
def sample_pet():
    return Pet(name="Biscuit", species="Dog", age=3)


# --- Tests ---

def test_mark_complete_changes_status(sample_task):
    """mark_complete() should flip is_completed from False to True."""
    assert sample_task.is_completed is False
    sample_task.mark_complete()
    assert sample_task.is_completed is True


def test_add_task_increases_pet_task_count(sample_pet, sample_task):
    """Adding a task to a Pet should increase its task list by one."""
    assert len(sample_pet.tasks) == 0
    sample_pet.add_task(sample_task)
    assert len(sample_pet.tasks) == 1
