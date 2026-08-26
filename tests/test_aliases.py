from pathlib import Path

from pricewatch.aliases import ModelAliases, normalized_key


def test_normalized_key_removes_vendor_and_normalizes_separators() -> None:
    assert normalized_key("Google/Gemini_2.5 Flash") == "gemini-2-5-flash"


def test_alias_table_maps_known_variants() -> None:
    aliases = ModelAliases(Path("config/model_aliases.json"))
    assert aliases.canonicalize("deepseek-ai/DeepSeek-V4-Flash") == "deepseek-v4-flash"
    assert aliases.canonicalize("claude-sonnet-4-20250514") == "claude-sonnet-4"
