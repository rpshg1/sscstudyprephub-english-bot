"""Format structured SSC English posts into clean Telegram HTML messages."""

import html
from typing import Callable, Dict, List
from pydantic import BaseModel

from .schemas import AfternoonPost, EveningPost, MorningPost
from .slots import SlotSpec


def _esc(text: str) -> str:
    """Escape dynamic text safely for Telegram HTML parse mode."""
    return html.escape(str(text).strip(), quote=False)


def _format_morning(post: MorningPost) -> List[str]:
    lines = ["📘 <b>5 High-Yield Vocabulary Words</b>"]
    for idx, item in enumerate(post.vocab, start=1):
        lines.append(
            f"{idx}. <b>{_esc(item.word)}</b> <i>({_esc(item.part_of_speech)})</i> — {_esc(item.meaning)}\n"
            f"   <i>Ex:</i> {_esc(item.example)}"
        )

    lines.append("\n🎯 <b>5 One-Word Substitutions (OWS)</b>")
    for idx, item in enumerate(post.ows, start=1):
        lines.append(
            f"{idx}. {_esc(item.phrase)} → <b>{_esc(item.word)}</b>\n"
            f"   <i>Ex:</i> {_esc(item.example)}"
        )
    return lines


def _format_afternoon(post: AfternoonPost) -> List[str]:
    lines = ["💡 <b>5 Idioms &amp; Phrases</b>"]
    for idx, item in enumerate(post.idioms, start=1):
        lines.append(
            f"{idx}. <b>{_esc(item.idiom)}</b> — {_esc(item.meaning)}\n"
            f"   <i>Ex:</i> {_esc(item.example)}"
        )

    lines.append("\n🔁 <b>5 Synonyms &amp; Antonyms</b>")
    for idx, item in enumerate(post.syn_ant, start=1):
        syns = ", ".join(_esc(s) for s in item.synonyms)
        ants = ", ".join(_esc(a) for a in item.antonyms)
        lines.append(
            f"{idx}. <b>{_esc(item.word)}</b> — {_esc(item.meaning)}\n"
            f"   <i>Syn:</i> {syns} | <i>Ant:</i> {ants}"
        )
    return lines


def _format_evening(post: EveningPost) -> List[str]:
    lines = ["⚖️ <b>5 Homonyms &amp; Homophones</b>"]
    for idx, item in enumerate(post.homonyms, start=1):
        lines.append(
            f"{idx}. <b>{_esc(item.word_1)}</b> ({_esc(item.meaning_1)}) "
            f"<b>vs</b> <b>{_esc(item.word_2)}</b> ({_esc(item.meaning_2)})\n"
            f"   <i>Ex:</i> {_esc(item.example_pair)}"
        )

    lines.append("\n✍️ <b>5 Spelling Boosters</b>")
    for idx, item in enumerate(post.spelling, start=1):
        wrong = ", ".join(_esc(w) for w in item.common_wrong_forms)
        lines.append(
            f"{idx}. ✅ <b>{_esc(item.correct_word)}</b> (❌ <i>{wrong}</i>) — {_esc(item.meaning)}\n"
            f"   <i>Tip:</i> {_esc(item.memory_tip)}"
        )
    return lines


SECTION_FORMATTERS: Dict[str, Callable[[BaseModel], List[str]]] = {
    "morning": _format_morning,
    "afternoon": _format_afternoon,
    "evening": _format_evening,
}


def format_post_html(spec: SlotSpec, post_data: BaseModel, date_label: str) -> str:
    """Render a full Telegram HTML message for the given slot and date."""
    header = (
        f"{spec.badge} | <b>{_esc(date_label)}</b>\n"
        f"🎓 <i>SSC CGL • CHSL • MTS • CPO • Steno • CDS</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    body_lines = SECTION_FORMATTERS[spec.name](post_data)
    footer = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 <i>Save &amp; revise daily before mock tests!</i>\n"
        "📢 <b>Join:</b> @sscstudyprephub | ▶️ <b>YouTube:</b> youtube.com/@sscstudyprephub"
    )
    return f"{header}\n\n" + "\n".join(body_lines) + f"\n\n{footer}"


def split_telegram_message(text: str, max_length: int = 4000) -> List[str]:
    """Split a long Telegram message on line breaks without exceeding max_length."""
    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    current = ""
    for line in text.split("\n"):
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= max_length:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        # Handle an unusually long single line safely.
        while len(line) > max_length:
            chunks.append(line[:max_length])
            line = line[max_length:]
        current = line

    if current:
        chunks.append(current)
    return chunks
