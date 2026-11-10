"""Slot metadata and IST time resolution for the 3 daily posts."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Type
from pydantic import BaseModel

from .schemas import AfternoonPost, EveningPost, MorningPost

IST = timezone(timedelta(hours=5, minutes=30))
ITEMS_PER_CATEGORY = 5


@dataclass(frozen=True)
class SlotSpec:
    """Configuration describing one of the three daily posting slots."""

    name: str
    badge: str
    schedule_label: str
    schema: Type[BaseModel]
    categories: Tuple[str, str]
    topic_instructions: str


SLOT_SPECS: Dict[str, SlotSpec] = {
    "morning": SlotSpec(
        name="morning",
        badge="🌅 Morning Dose",
        schedule_label="7:00 AM IST",
        schema=MorningPost,
        categories=("vocab", "ows"),
        topic_instructions=(
            "1) 5 high-yield SSC/government-exam English Vocabulary words (vocab) "
            "frequently tested in SSC CGL, CHSL, CPO, MTS, and CDS.\n"
            "2) 5 high-yield One-Word Substitutions (ows) frequently asked in SSC PYQs."
        ),
    ),
    "afternoon": SlotSpec(
        name="afternoon",
        badge="☀️ Afternoon Dose",
        schedule_label="1:00 PM IST",
        schema=AfternoonPost,
        categories=("idioms", "syn_ant"),
        topic_instructions=(
            "1) 5 high-yield English Idioms & Phrases (idioms) tested in SSC CGL, CHSL, CPO, and MTS.\n"
            "2) 5 high-yield Synonym-Antonym word sets (syn_ant) with 2-3 accurate SSC synonyms and 2-3 antonyms each."
        ),
    ),
    "evening": SlotSpec(
        name="evening",
        badge="🌙 Evening Dose",
        schedule_label="7:00 PM IST",
        schema=EveningPost,
        categories=("homonyms", "spelling"),
        topic_instructions=(
            "1) 5 commonly confused Homonyms / Homophones pairs (homonyms) tested in SSC exams.\n"
            "2) 5 tricky Spelling words (spelling) frequently tested in SSC spelling-error questions, "
            "with common wrong spellings and a concise memory tip."
        ),
    ),
}


def current_ist_now() -> datetime:
    """Return the current timezone-aware datetime in IST (UTC+05:30)."""
    return datetime.now(IST)


def resolve_slot(requested: str = "auto", now_ist: datetime | None = None) -> SlotSpec:
    """Resolve explicit slot name or infer slot from current IST time."""
    normalized = (requested or "auto").strip().lower()
    if normalized != "auto":
        if normalized not in SLOT_SPECS:
            valid = ", ".join(SLOT_SPECS.keys())
            raise ValueError(f"Unsupported slot '{requested}'. Expected one of: auto, {valid}")
        return SLOT_SPECS[normalized]

    dt = now_ist or current_ist_now()
    minutes = dt.hour * 60 + dt.minute
    if minutes < 11 * 60 + 30:
        return SLOT_SPECS["morning"]
    if minutes < 17 * 60:
        return SLOT_SPECS["afternoon"]
    return SLOT_SPECS["evening"]
