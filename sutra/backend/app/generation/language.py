"""
generation/language.py — Language handling utilities.
Manages target language for generation: the system always extracts facts
in the source language but generates output in the operator-selected target.
Supports: en, hi (Hindi/Devanagari), ta (Tamil).
"""
from __future__ import annotations

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
}

LANGUAGE_INSTRUCTIONS = {
    "en": "Generate all output text in English.",
    "hi": (
        "Generate all output text in Hindi using Devanagari script. "
        "Use formal Hindi (shuddh Hindi) appropriate for government communication. "
        "Numbers may remain in Arabic numerals."
    ),
    "ta": (
        "Generate all output text in Tamil using Tamil script. "
        "Use formal written Tamil appropriate for official documents. "
        "Numbers may remain in Arabic numerals."
    ),
}

FONT_REQUIREMENTS = {
    "en": "Noto Sans",
    "hi": "Noto Sans Devanagari",
    "ta": "Noto Sans Tamil",
}


def language_instruction(lang_code: str) -> str:
    """Return the language instruction to prepend to every generation prompt."""
    return LANGUAGE_INSTRUCTIONS.get(lang_code, LANGUAGE_INSTRUCTIONS["en"])


def required_font(lang_code: str) -> str:
    """Return the font family required to render this language."""
    return FONT_REQUIREMENTS.get(lang_code, "Noto Sans")


def validate_language(lang_code: str) -> bool:
    """Return True if the language code is supported."""
    return lang_code in SUPPORTED_LANGUAGES


def language_name(lang_code: str) -> str:
    """Human-readable language name."""
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)
