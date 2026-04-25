"""
test_rag.py — automated tests for the RAG pipeline (rag.py)

Covers the three functions that can be tested without any API calls:
  1. get_age_group   — maps species + age to a KB age-group key
  2. retrieve_facts  — looks up care facts from the knowledge base
  3. build_prompt    — assembles the LLM prompt from plan + facts
  4. load_knowledge_base — file loading with error handling

No Groq / LLM calls are made. The _call_with_retry and generate_advice
functions are excluded because they require a live API key.
"""

import pytest
from datetime import date

import rag
from rag import get_age_group, retrieve_facts, build_prompt, load_knowledge_base
from pawpal_system import Owner, Task, Priority, DailyPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_plan(scheduled=None, skipped=None, reasoning=None):
    owner = Owner(name="Test", available_minutes_per_day=60)
    plan = DailyPlan(owner=owner)
    plan.scheduled = scheduled or []
    plan.skipped = skipped or []
    plan.reasoning = reasoning or {}
    plan.total_time_used = sum(t.duration_minutes for t in plan.scheduled)
    return plan


def make_task(name="Walk", category="walk", duration=20,
              priority=Priority.HIGH, time="09:00"):
    return Task(name=name, category=category, duration_minutes=duration,
                priority=priority, scheduled_time=time)


# ---------------------------------------------------------------------------
# 1 — get_age_group
# ---------------------------------------------------------------------------

def test_dog_puppy():
    """Dogs under 1 year are classified as puppies."""
    assert get_age_group("dog", 0) == "puppy"


def test_dog_adult():
    """Dogs aged 1–6 are classified as adults."""
    assert get_age_group("dog", 3) == "adult"


def test_dog_senior():
    """Dogs aged 7+ are classified as seniors."""
    assert get_age_group("dog", 7) == "senior"


def test_cat_kitten():
    """Cats under 1 year are classified as kittens."""
    assert get_age_group("cat", 0) == "kitten"


def test_cat_adult():
    """Cats aged 1–9 are classified as adults."""
    assert get_age_group("cat", 5) == "adult"


def test_cat_senior():
    """Cats aged 10+ are classified as seniors."""
    assert get_age_group("cat", 10) == "senior"


def test_unknown_species_defaults_to_adult():
    """Any species not explicitly handled returns 'adult' as a safe fallback."""
    assert get_age_group("hamster", 2) == "adult"


# ---------------------------------------------------------------------------
# 2 — retrieve_facts
# ---------------------------------------------------------------------------

def test_walk_returns_exercise_fact_for_adult_dog():
    """'walk' category maps to KB 'exercise' and returns an age-matched fact."""
    facts = retrieve_facts("dog", 3, ["walk"])
    assert len(facts) == 1
    assert "[EXERCISE]" in facts[0]


def test_feed_returns_feeding_fact_for_adult_cat():
    """'feed' category maps to KB 'feeding' and returns a fact for adult cats."""
    facts = retrieve_facts("cat", 5, ["feed"])
    assert len(facts) == 1
    assert "[FEEDING]" in facts[0]


def test_meds_returns_health_fact_for_rabbit():
    """'meds' category maps to KB 'health' and returns a fact for rabbits."""
    facts = retrieve_facts("rabbit", 2, ["meds"])
    assert len(facts) == 1
    assert "[HEALTH]" in facts[0]


def test_multiple_categories_return_one_fact_each():
    """Three distinct categories each contribute one retrieved fact."""
    facts = retrieve_facts("dog", 3, ["walk", "feed", "grooming"])
    assert len(facts) == 3


def test_duplicate_categories_are_deduplicated():
    """Passing the same category twice only retrieves one fact, not two."""
    facts = retrieve_facts("dog", 3, ["walk", "walk"])
    assert len(facts) == 1


def test_unknown_category_skipped_silently():
    """A category absent from CATEGORY_TO_KB_KEY returns [] without crashing."""
    facts = retrieve_facts("dog", 3, ["unknown_xyz"])
    assert facts == []


def test_empty_categories_returns_empty_list():
    """An empty category list returns no facts."""
    facts = retrieve_facts("dog", 3, [])
    assert facts == []


def test_puppy_gets_puppy_specific_fact():
    """A dog aged 0 gets the puppy exercise fact, not the adult one."""
    facts = retrieve_facts("dog", 0, ["walk"])
    assert "Puppies" in facts[0]


def test_senior_dog_gets_senior_fact():
    """A dog aged 8 gets the senior exercise fact."""
    facts = retrieve_facts("dog", 8, ["walk"])
    assert "Senior" in facts[0]


def test_unknown_species_does_not_crash():
    """An unlisted species falls back to 'other' without raising an error."""
    facts = retrieve_facts("hamster", 2, ["walk"])
    assert isinstance(facts, list)


def test_general_category_maps_to_health():
    """'general' category maps to 'health' section and retrieves a health fact for dogs."""
    facts = retrieve_facts("dog", 3, ["general"])
    assert len(facts) == 1
    assert "[HEALTH]" in facts[0]


# ---------------------------------------------------------------------------
# 3 — build_prompt
# ---------------------------------------------------------------------------

def test_prompt_contains_scheduled_task_name():
    """Each scheduled task's name appears in the built prompt."""
    task = make_task(name="Morning Walk")
    plan = make_plan(scheduled=[task])
    prompt = build_prompt(plan, "Mochi", "dog", ["[EXERCISE] fact."])
    assert "Morning Walk" in prompt


def test_prompt_shows_none_when_no_skipped_tasks():
    """The skipped block shows 'None' when plan.skipped is empty."""
    plan = make_plan(scheduled=[make_task()])
    prompt = build_prompt(plan, "Mochi", "dog", ["[EXERCISE] fact."])
    assert "None" in prompt


def test_prompt_includes_skipped_task_name():
    """A skipped task's name and reason appear in the prompt."""
    skipped = make_task(name="Brush Coat")
    plan = make_plan(
        scheduled=[make_task()],
        skipped=[skipped],
        reasoning={"Brush Coat": "not enough time"},
    )
    prompt = build_prompt(plan, "Mochi", "dog", ["[GROOMING] fact."])
    assert "Brush Coat" in prompt


def test_prompt_contains_retrieved_facts():
    """Retrieved facts appear verbatim inside the prompt."""
    fact = "[EXERCISE] Adult dogs need 30–60 minutes daily."
    plan = make_plan(scheduled=[make_task()])
    prompt = build_prompt(plan, "Mochi", "dog", [fact])
    assert fact in prompt


def test_prompt_contains_pet_name_and_species():
    """The prompt references the pet's name and species."""
    plan = make_plan(scheduled=[make_task()])
    prompt = build_prompt(plan, "Luna", "cat", ["[FEEDING] fact."])
    assert "Luna" in prompt
    assert "cat" in prompt


def test_prompt_shows_no_facts_placeholder_when_empty():
    """An empty facts list causes the 'No specific facts retrieved' placeholder."""
    plan = make_plan(scheduled=[make_task()])
    prompt = build_prompt(plan, "Mochi", "dog", [])
    assert "No specific facts retrieved" in prompt


# ---------------------------------------------------------------------------
# 4 — load_knowledge_base (error handling)
# ---------------------------------------------------------------------------

def test_missing_kb_file_returns_empty_dict(monkeypatch):
    """A missing KB file returns {} instead of raising FileNotFoundError."""
    monkeypatch.setattr(rag, "KB_PATH", "/nonexistent/path/kb.json")
    result = load_knowledge_base()
    assert result == {}


def test_corrupt_kb_file_returns_empty_dict(tmp_path, monkeypatch):
    """A corrupt KB file returns {} instead of raising JSONDecodeError."""
    bad_file = tmp_path / "kb.json"
    bad_file.write_text("this is not json {{ broken")
    monkeypatch.setattr(rag, "KB_PATH", str(bad_file))
    result = load_knowledge_base()
    assert result == {}


def test_valid_kb_contains_expected_species():
    """The real KB file loads and contains dog, cat, and rabbit sections."""
    kb = load_knowledge_base()
    assert "dog" in kb
    assert "cat" in kb
    assert "rabbit" in kb


def test_valid_kb_dog_has_exercise_section():
    """The dog section of the real KB contains an 'exercise' key."""
    kb = load_knowledge_base()
    assert "exercise" in kb["dog"]
    assert "adult" in kb["dog"]["exercise"]
