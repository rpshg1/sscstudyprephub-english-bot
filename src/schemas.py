"""Pydantic schemas for structured Gemini output across daily slots."""

from typing import List
from pydantic import BaseModel, Field


class VocabItem(BaseModel):
    """A single high-yield SSC vocabulary entry."""

    word: str = Field(description="Target English word suitable for SSC CGL/CHSL/CPO.")
    part_of_speech: str = Field(description="Short part of speech, e.g. adj., verb, noun.")
    meaning: str = Field(description="Clear, concise exam-focused meaning in 1 line.")
    example: str = Field(description="Short natural sentence showing the word in context.")


class OwsItem(BaseModel):
    """A single One-Word Substitution (OWS) entry."""

    phrase: str = Field(description="Descriptive phrase or definition asked in SSC exams.")
    word: str = Field(description="Exact one-word substitution for the phrase.")
    example: str = Field(description="Short example sentence using the substituted word.")


class MorningPost(BaseModel):
    """7:00 AM IST post: 5 Vocabulary words + 5 One-Word Substitutions."""

    vocab: List[VocabItem] = Field(description="Exactly 5 unique SSC vocabulary items.")
    ows: List[OwsItem] = Field(description="Exactly 5 unique one-word substitution items.")


class IdiomItem(BaseModel):
    """A single Idiom or Phrase entry."""

    idiom: str = Field(description="Exam-relevant English idiom or phrase.")
    meaning: str = Field(description="Concise meaning of the idiom.")
    example: str = Field(description="Short sentence illustrating the idiom.")


class SynAntItem(BaseModel):
    """A single Synonym & Antonym entry."""

    word: str = Field(description="Target SSC English word.")
    meaning: str = Field(description="Brief meaning of the target word.")
    synonyms: List[str] = Field(description="2 or 3 accurate SSC-level synonyms.")
    antonyms: List[str] = Field(description="2 or 3 accurate SSC-level antonyms.")


class AfternoonPost(BaseModel):
    """1:00 PM IST post: 5 Idioms & Phrases + 5 Synonyms & Antonyms."""

    idioms: List[IdiomItem] = Field(description="Exactly 5 unique idioms and phrases.")
    syn_ant: List[SynAntItem] = Field(description="Exactly 5 unique synonym-antonym entries.")


class HomonymItem(BaseModel):
    """A pair of commonly confused homonyms or homophones."""

    word_1: str = Field(description="First word in the confused pair.")
    meaning_1: str = Field(description="Brief meaning of the first word.")
    word_2: str = Field(description="Second word in the confused pair.")
    meaning_2: str = Field(description="Brief meaning of the second word.")
    example_pair: str = Field(description="One or two short sentences contrasting both words.")


class SpellingItem(BaseModel):
    """A commonly misspelled SSC exam word entry."""

    correct_word: str = Field(description="Correctly spelled English word.")
    common_wrong_forms: List[str] = Field(description="1 or 2 common incorrect spellings students confuse.")
    meaning: str = Field(description="Short meaning of the word.")
    memory_tip: str = Field(description="Quick trick to remember the exact spelling.")


class EveningPost(BaseModel):
    """7:00 PM IST post: 5 Homonyms/Homophones + 5 Spelling rules."""

    homonyms: List[HomonymItem] = Field(description="Exactly 5 unique homonym/homophone pairs.")
    spelling: List[SpellingItem] = Field(description="Exactly 5 unique tricky spelling entries.")
