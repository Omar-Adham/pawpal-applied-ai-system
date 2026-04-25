import json
import logging
import os
import time

from groq import Groq, RateLimitError
from dotenv import load_dotenv

from pawpal_system import DailyPlan, Owner

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

KB_PATH = os.path.join(os.path.dirname(__file__), "pet_care_kb.json")

CATEGORY_TO_KB_KEY = {
    "walk":       "exercise",
    "enrichment": "enrichment",
    "feed":       "feeding",
    "meds":       "health",
    "grooming":   "grooming",
    "general":    "health",
    "other":      "health",
}


def load_knowledge_base() -> dict:
    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Knowledge base file not found at %s", KB_PATH)
        return {}
    except json.JSONDecodeError as e:
        logger.error("Knowledge base file is corrupt: %s", e)
        return {}


def get_age_group(species: str, age: int) -> str:
    if species == "dog":
        if age < 1:
            return "puppy"
        if age >= 7:
            return "senior"
        return "adult"
    if species == "cat":
        if age < 1:
            return "kitten"
        if age >= 10:
            return "senior"
        return "adult"
    return "adult"


def retrieve_facts(species: str, age: int, task_categories: list[str]) -> list[str]:
    """Return relevant care facts from the KB for the given pet and task categories."""
    kb = load_knowledge_base()
    if not kb:
        return []
    species_key = species.lower() if species.lower() in kb else "other"
    if species_key not in kb:
        logger.warning("Species '%s' not found in KB and no 'other' fallback.", species)
        return []
    species_data = kb[species_key]
    age_group = get_age_group(species_key, age)

    facts = []
    seen_keys = set()

    for category in task_categories:
        kb_key = CATEGORY_TO_KB_KEY.get(category.lower())
        if not kb_key or kb_key in seen_keys:
            continue
        seen_keys.add(kb_key)

        section = species_data.get(kb_key, {})
        if not section:
            continue

        # Prefer age-specific fact, fall back to "general"
        fact = section.get(age_group) or section.get("general")
        if fact:
            facts.append(f"[{kb_key.upper()}] {fact}")
            logger.info("Retrieved fact — species=%s key=%s age_group=%s", species_key, kb_key, age_group)

    return facts


def build_prompt(plan: DailyPlan, pet_name: str, species: str, facts: list[str]) -> str:
    scheduled_lines = "\n".join(
        f"  - {t.scheduled_time}  {t.name} ({t.duration_minutes} min, {t.priority.name})"
        for t in plan.scheduled
    )
    skipped_lines = "\n".join(
        f"  - {t.name}: {plan.reasoning.get(t.name, 'no reason given')}"
        for t in plan.skipped
    ) or "  None"

    facts_block = "\n".join(f"  {f}" for f in facts) if facts else "  No specific facts retrieved."

    return f"""You are a knowledgeable and friendly pet care assistant.

A pet owner has generated a daily care schedule for their {species} named {pet_name}.
Use ONLY the care facts provided below to give a short, specific advice note (3-5 sentences).
Do not add information that is not in the facts. Be practical and encouraging.

--- TODAY'S SCHEDULE ---
Scheduled tasks:
{scheduled_lines}

Skipped tasks:
{skipped_lines}

--- RETRIEVED CARE FACTS ---
{facts_block}

Write a short advice note for the owner based on the schedule and the facts above.
"""


def _call_with_retry(client: Groq, prompt: str, pet_name: str, retries: int = 3) -> str:
    delay = 10
    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
            )
            advice = response.choices[0].message.content.strip()
            logger.info("Received advice for pet=%s (%d chars)", pet_name, len(advice))
            return advice
        except RateLimitError as e:
            if attempt < retries:
                logger.warning(
                    "Rate limit hit for pet=%s (attempt %d/%d) — retrying in %ds",
                    pet_name, attempt, retries, delay,
                )
                time.sleep(delay)
                delay *= 2
            else:
                logger.error("Rate limit exhausted for pet=%s after %d attempts.", pet_name, retries)
                return (
                    "AI advice unavailable — Groq rate limit exceeded. "
                    "Wait a moment and try again."
                )
        except Exception as e:
            logger.error("Groq API error for pet=%s: %s", pet_name, e)
            return f"AI advice unavailable — {e}"
    return "AI advice unavailable — unknown error."


def generate_advice(plan: DailyPlan, owner: Owner) -> str:
    """
    Main RAG function. Retrieves facts for each pet, calls Groq,
    and returns a grounded advice note. Falls back gracefully on error.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set — skipping AI advice.")
        return "AI advice unavailable: GROQ_API_KEY not configured."

    if not owner.pets:
        return "No pets registered — add a pet to receive AI care advice."

    if not plan.scheduled:
        return "No tasks were scheduled — add tasks or adjust your available time to get AI advice."

    client = Groq(api_key=api_key)

    all_advice = []

    for pet in owner.pets:
        task_categories = list({t.category for t in pet.tasks})
        logger.info(
            "Retrieving facts for pet=%s species=%s age=%d categories=%s",
            pet.name, pet.species, pet.age, task_categories,
        )

        facts = retrieve_facts(pet.species, pet.age, task_categories)

        if not facts:
            logger.warning("No facts retrieved for pet=%s — skipping AI call.", pet.name)
            all_advice.append(f"**{pet.name}:** No specific care facts found for this pet type.")
            continue

        prompt = build_prompt(plan, pet.name, pet.species, facts)
        logger.info("Sending prompt to Groq for pet=%s", pet.name)

        advice = _call_with_retry(client, prompt, pet.name)
        all_advice.append(f"**{pet.name}:** {advice}")

    return "\n\n".join(all_advice) if all_advice else "No advice generated — check that your pet's species and task categories are covered in the knowledge base."
