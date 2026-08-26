from __future__ import annotations

import json
import re
from pathlib import Path


def normalized_key(name: str) -> str:
    value = name.strip().lower().replace("_", "-")
    value = re.sub(r"^(?:openai|anthropic|google|qwen|deepseek-ai)/", "", value)
    value = re.sub(r"[.\s]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


class ModelAliases:
    def __init__(self, path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._lookup: dict[str, str] = {}
        for canonical, aliases in raw.items():
            canonical_key = normalized_key(canonical)
            self._lookup[canonical_key] = canonical_key
            for alias in aliases:
                self._lookup[normalized_key(alias)] = canonical_key

    def canonicalize(self, name: str) -> str:
        key = normalized_key(name)
        return self._lookup.get(key, key)
