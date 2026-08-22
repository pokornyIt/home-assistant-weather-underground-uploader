"""Tests for integration translation resources."""

import json
import re
from pathlib import Path
from typing import cast

TRANSLATIONS_DIR = Path(__file__).parents[1] / "custom_components" / "weather_underground_uploader" / "translations"
PLACEHOLDER_PATTERN = re.compile(r"{[^{}]+}")
type TranslationValue = str | dict[str, "TranslationValue"]


def _load_translation(language: str) -> dict[str, TranslationValue]:
    """Load an integration translation file."""
    with (TRANSLATIONS_DIR / f"{language}.json").open(encoding="utf-8") as file:
        return cast(dict[str, TranslationValue], json.load(file))


def _leaf_values(value: TranslationValue, path: tuple[str, ...] = ()) -> dict[tuple[str, ...], str]:
    """Return string leaves keyed by their full translation path."""
    if isinstance(value, dict):
        leaves: dict[tuple[str, ...], str] = {}
        for key, child in value.items():
            leaves.update(_leaf_values(child, (*path, key)))
        return leaves

    assert isinstance(value, str), f"Translation value at {'.'.join(path)} must be a string"
    assert value.strip(), f"Translation value at {'.'.join(path)} must not be empty"
    return {path: value}


def test_czech_translation_matches_english_structure() -> None:
    """Czech and English expose identical keys and placeholders."""
    english = _leaf_values(_load_translation("en"))
    czech = _leaf_values(_load_translation("cs"))

    assert czech.keys() == english.keys()
    for path, english_text in english.items():
        assert PLACEHOLDER_PATTERN.findall(czech[path]) == PLACEHOLDER_PATTERN.findall(english_text)


def test_czech_translation_preserves_protocol_identifiers() -> None:
    """Weather Underground credential identifiers remain unchanged."""
    czech = _leaf_values(_load_translation("cs"))

    assert czech[("config", "step", "user", "data", "station_id")] == "Station ID"
    assert czech[("config", "step", "user", "data", "station_key")] == "Station Key"


def test_mapping_guidance_is_separate_and_emphasized() -> None:
    """Initial setup highlights the follow-up mapping step in each language."""
    for language, label in {"en": "Next step", "cs": "Další krok"}.items():
        translations = _leaf_values(_load_translation(language))
        description = translations[("config", "step", "user", "description")]
        assert f"\n\n**{label}:**" in description
