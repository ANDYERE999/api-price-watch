from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class PriceRecord:
    provider_id: str
    provider_name: str
    source_url: str
    source_model: str
    canonical_model: str
    group: str
    billing_mode: str
    currency: str
    captured_at: str
    input_per_million: float | None = None
    output_per_million: float | None = None
    cache_read_per_million: float | None = None
    cache_write_per_million: float | None = None
    request_price: float | None = None
    condition: str = ""
    multiplier: float | None = None
    available: bool = True
    metadata: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def history_key(self) -> str:
        return "|".join(
            (
                self.provider_id,
                self.canonical_model,
                self.group,
                self.billing_mode,
                self.condition,
            )
        )
