"""Gemini API structured content generator with deduplication and transient retries."""

import os
import time
from typing import Callable, Dict, List, Optional
from google import genai
from pydantic import BaseModel

from .history_store import find_duplicates
from .slots import ITEMS_PER_CATEGORY, SlotSpec

DEFAULT_MODEL = "gemini-3.8-flash"
MAX_EXCLUSION_ITEMS = 400

SYSTEM_INSTRUCTION = (
    "You are an expert English faculty preparing content for Indian government exam aspirants "
    "(SSC CGL, SSC CHSL, SSC MTS, SSC CPO, Stenographer, CDS, and Banking). "
    "Provide accurate, concise, exam-oriented definitions, natural examples, and zero spelling errors. "
    "Strictly return JSON matching the requested schema with exactly 5 distinct items per list, "
    "never repeating any term from the exclusion list."
)


def _build_prompt(
    spec: SlotSpec,
    history: dict,
    extra_exclusions: Dict[str, List[str]] | None = None,
) -> str:
    """Build a generation prompt including previously posted exclusions."""
    extra_exclusions = extra_exclusions or {}
    exclusion_lines: List[str] = []
    for cat in spec.categories:
        combined = list(history.get(cat, [])) + list(extra_exclusions.get(cat, []))
        recent = combined[-MAX_EXCLUSION_ITEMS:]
        joined = ", ".join(recent) if recent else "None yet"
        exclusion_lines.append(f"- {cat} already posted (DO NOT repeat any of these): {joined}")

    return (
        f"Generate content for the {spec.name.upper()} ({spec.schedule_label}) capsule.\n\n"
        f"Required sections (EXACTLY {ITEMS_PER_CATEGORY} items in each section):\n"
        f"{spec.topic_instructions}\n\n"
        "Exclusion lists (you MUST choose completely fresh items not present below):\n"
        + "\n".join(exclusion_lines)
    )


class MissingApiKeyError(RuntimeError):
    """Raised immediately when GEMINI_API_KEY is not configured."""


def _default_invoke_gemini(spec: SlotSpec, prompt: str, model: str) -> BaseModel:
    """Invoke Gemini Interactions API and validate JSON output into the slot schema."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise MissingApiKeyError(
            "GEMINI_API_KEY is missing. Set it in .env locally or as a GitHub Actions Secret."
        )

    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=model,
        system_instruction=SYSTEM_INSTRUCTION,
        input=prompt,
        store=False,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": spec.schema.model_json_schema(),
        },
    )
    if not interaction.output_text:
        raise RuntimeError("Gemini returned an empty response.")
    return spec.schema.model_validate_json(interaction.output_text)


def generate_unique_post(
    spec: SlotSpec,
    history: dict,
    model: str = DEFAULT_MODEL,
    max_attempts: int = 3,
    retry_delay: float = 5.0,
    invoker: Optional[Callable[[SlotSpec, str, str], BaseModel]] = None,
) -> BaseModel:
    """Generate a slot post with exactly 5 non-duplicate items per category."""
    call_model = invoker or _default_invoke_gemini
    extra_exclusions: Dict[str, List[str]] = {cat: [] for cat in spec.categories}
    last_error = "Unknown generation failure"

    for attempt in range(1, max_attempts + 1):
        prompt = _build_prompt(spec, history, extra_exclusions)
        try:
            post_data = call_model(spec, prompt, model)
        except MissingApiKeyError:
            raise
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"[Attempt {attempt}/{max_attempts}] Gemini call error: {last_error}")
            if attempt < max_attempts and retry_delay > 0:
                time.sleep(retry_delay * attempt)
            continue

        issues: List[str] = []
        for cat in spec.categories:
            items = getattr(post_data, cat)
            if len(items) != ITEMS_PER_CATEGORY:
                issues.append(f"{cat} returned {len(items)} items (expected {ITEMS_PER_CATEGORY})")
                continue

            collisions = find_duplicates(cat, items, history.get(cat, []))
            if collisions:
                issues.append(f"{cat} repeated: {', '.join(collisions)}")
                extra_exclusions[cat].extend(c for c in collisions if c != "<empty>")

        if not issues:
            return post_data

        last_error = "; ".join(issues)
        print(f"[Attempt {attempt}/{max_attempts}] Retrying due to validation issue: {last_error}")

    raise RuntimeError(
        f"Failed to generate {ITEMS_PER_CATEGORY} unique items after {max_attempts} attempts: {last_error}"
    )
