"""History loading, saving, and duplicate-key tracking across all 6 topics."""

import json
import re
from pathlib import Path
from typing import Callable, Dict, List, Tuple
from pydantic import BaseModel

CATEGORIES: Tuple[str, ...] = (
    "vocab",
    "ows",
    "idioms",
    "syn_ant",
    "homonyms",
    "spelling",
)


def normalize_text(text: str) -> str:
    """Normalize a single term or phrase for case/punctuation-insensitive matching."""
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return " ".join(cleaned.split())


def normalize_homonym_pair(word_1: str, word_2: str) -> str:
    """Normalize a homonym pair symmetrically so order doesn't mask duplicates."""
    pair = sorted([normalize_text(word_1), normalize_text(word_2)])
    return f"{pair[0]} | {pair[1]}"


def _extract_vocab_key(item) -> str:
    return normalize_text(item.word)


def _extract_ows_key(item) -> str:
    return normalize_text(item.word)


def _extract_idiom_key(item) -> str:
    return normalize_text(item.idiom)


def _extract_syn_ant_key(item) -> str:
    return normalize_text(item.word)


def _extract_homonym_key(item) -> str:
    return normalize_homonym_pair(item.word_1, item.word_2)


def _extract_spelling_key(item) -> str:
    return normalize_text(item.correct_word)


KEY_EXTRACTORS: Dict[str, Callable[[object], str]] = {
    "vocab": _extract_vocab_key,
    "ows": _extract_ows_key,
    "idioms": _extract_idiom_key,
    "syn_ant": _extract_syn_ant_key,
    "homonyms": _extract_homonym_key,
    "spelling": _extract_spelling_key,
}


def empty_history() -> dict:
    """Return a fresh empty history dictionary."""
    data = {cat: [] for cat in CATEGORIES}
    data["posted_log"] = []
    return data


def load_history(path: Path) -> dict:
    """Load history JSON from disk, filling in missing keys safely."""
    if not path.exists():
        return empty_history()
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    history = empty_history()
    for cat in CATEGORIES:
        history[cat] = [str(item) for item in raw.get(cat, [])]
    history["posted_log"] = [str(entry) for entry in raw.get("posted_log", [])]
    return history


def save_history(path: Path, history: dict) -> None:
    """Persist history JSON cleanly to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def already_posted_slot(history: dict, date_ist: str, slot: str) -> bool:
    """Return True if the given IST date + slot has already been posted."""
    return f"{date_ist}:{slot}" in set(history.get("posted_log", []))


def extract_category_keys(category: str, items: List[object]) -> List[str]:
    """Extract normalized deduplication keys for items in a category."""
    extractor = KEY_EXTRACTORS[category]
    return [extractor(item) for item in items]


def find_duplicates(
    category: str, items: List[object], existing_keys: List[str]
) -> List[str]:
    """Return any keys in items that collide with existing history or repeat inside items."""
    seen = set(existing_keys)
    collisions: List[str] = []
    for key in extract_category_keys(category, items):
        if not key or key in seen:
            collisions.append(key or "<empty>")
        else:
            seen.add(key)
    return collisions


def record_posted_items(
    history: dict,
    categories: Tuple[str, str],
    post_data: BaseModel,
    date_ist: str,
    slot: str,
) -> None:
    """Append newly posted items and slot execution marker to history in place."""
    for cat in categories:
        items = getattr(post_data, cat)
        existing = set(history[cat])
        for key in extract_category_keys(cat, items):
            if key and key not in existing:
                history[cat].append(key)
                existing.add(key)

    marker = f"{date_ist}:{slot}"
    if marker not in history["posted_log"]:
        history["posted_log"].append(marker)
