from pathlib import Path

import pytest

from pricewatch.aliases import ModelAliases
from pricewatch.collectors.new_api import collect_new_api


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeClient:
    def get(self, url: str) -> FakeResponse:
        if url.endswith("/api/status"):
            return FakeResponse({"data": {"quota_per_unit": 500_000, "quota_display_type": "CNY"}})
        return FakeResponse(
            {
                "data": [
                    {
                        "model_name": "test-model",
                        "quota_type": 0,
                        "model_ratio": 1.5,
                        "completion_ratio": 5,
                        "enable_groups": ["cheap", "official"],
                    }
                ],
                "group_ratio": {"cheap": 0.2, "official": 6},
            }
        )


def test_new_api_applies_each_group_ratio() -> None:
    aliases = ModelAliases(Path("config/model_aliases.json"))
    records = collect_new_api(
        {"id": "test", "name": "Test", "base_url": "https://example.com", "pricing_url": "https://example.com/pricing"},
        FakeClient(),  # type: ignore[arg-type]
        aliases,
        "2026-01-01T00:00:00Z",
    )
    assert [record.group for record in records] == ["cheap", "official"]
    assert [record.input_per_million for record in records] == pytest.approx([0.6, 18.0])
