"""Gemini API structured content generator with model fallback and deduplication."""

import os
import time
from typing import Callable, Dict, List, Optional, Tuple
from google import genai
from google.genai import types
from pydantic import BaseModel

from .history_store import find_duplicates
from .slots import ITEMS_PER_CATEGORY, SlotSpec

DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODELS: Tuple[str, ...] = (
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-4-argon",
)
MAX_EXCLUSION_ITEMS = 400

SYSTEM_INSTRUCTION = (
    "You are an expert English faculty preparing content for Indian government exam aspirants "
    "(SSC CGL, SSC CHSL, SSC MTS, SSC CPO, Stenographer, CDS, and Banking). "
    "Provide accurate, concise, exam-oriented definitions, natural examples, and zero spelling errors. "
    "Strictly return JSON matching the requested schema with exactly 5 distinct items per list, "
    "never repeating any term from the exclusion list."
)


class MissingApiKeyError(RuntimeError):
    """Raised immediately when GEMINI_API_KEY is not configured."""


def build_model_chain(primary_model: str) -> List[str]:
    """Return ordered unique model list starting with primary_model."""
    primary = (primary_model or DEFAULT_MODEL).strip()
    chain = [primary]
    for candidate in FALLBACK_MODELS:
        if candidate not in chain:
            chain.append(candidate)
    return chain


def _is_invalid_api_key_error(exc: Exception) -> bool:
    """Detect fatal invalid-API-key errors that will fail across all models."""
    msg = str(exc).lower()
    return "api_key_invalid" in msg or "api key not valid" in msg or "unauthenticated" in msg


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


def _default_invoke_gemini(spec: SlotSpec, prompt: str, model: str) -> BaseModel:
    """Invoke Gemini Generate Content API with bounded HTTP retries so fallback is fast."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise MissingApiKeyError(
            "GEMINI_API_KEY is missing. Set it in .env locally or as a GitHub Actions Secret."
        )

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=45_000,
            retry_options=types.HttpRetryOptions(
                attempts=2,
                initial_delay=1.0,
                max_delay=4.0,
            ),
        ),
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=spec.schema,
        ),
    )
    if response.parsed:
        return response.parsed
    if response.text:
        return spec.schema.model_validate_json(response.text)
    raise RuntimeError(f"Model '{model}' returned an empty response.")


def generate_unique_post(
    spec: SlotSpec,
    history: dict,
    model: str = DEFAULT_MODEL,
    max_attempts: int = 3,
    retry_delay: float = 5.0,
    invoker: Optional[Callable[[SlotSpec, str, str], BaseModel]] = None,
) -> BaseModel:
    """Generate a slot post with automatic model fallback and deduplication."""
    call_model = invoker or _default_invoke_gemini
    model_chain = build_model_chain(model)
    extra_exclusions: Dict[str, List[str]] = {cat: [] for cat in spec.categories}
    last_error = "Unknown generation failure"

    for pass_num in (1, 2):
        for active_model in model_chain:
            for attempt in range(1, max_attempts + 1):
                prompt = _build_prompt(spec, history, extra_exclusions)
                try:
                    post_data = call_model(spec, prompt, active_model)
                except MissingApiKeyError:
                    raise
                except Exception as exc:
                    if _is_invalid_api_key_error(exc):
                        raise
                    last_error = f"{active_model}: {type(exc).__name__}: {exc}"
                    print(f"[Fallback] {last_error}")
                    break

                issues: List[str] = []
                for cat in spec.categories:
                    items = getattr(post_data, cat)
                    if len(items) != ITEMS_PER_CATEGORY:
                        issues.append(
                            f"{cat} returned {len(items)} items (expected {ITEMS_PER_CATEGORY})"
                        )
                        continue

                    collisions = find_duplicates(cat, items, history.get(cat, []))
                    if collisions:
                        issues.append(f"{cat} repeated: {', '.join(collisions)}")
                        extra_exclusions[cat].extend(c for c in collisions if c != "<empty>")

                if not issues:
                    print(f"[Generated] Content ready using model '{active_model}'.")
                    return post_data

                last_error = f"{active_model}: {'; '.join(issues)}"
                print(
                    f"[Attempt {attempt}/{max_attempts}] Retrying '{active_model}' due to validation issue: {last_error}"
                )

        if pass_num == 1 and retry_delay > 0:
            print(f"[Retry] All models in fallback chain failed; waiting {retry_delay}s before second pass...")
            time.sleep(retry_delay)

    raise RuntimeError(
        f"Failed to generate {ITEMS_PER_CATEGORY} unique items after fallback attempts: {last_error}"
    )
