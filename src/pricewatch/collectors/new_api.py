from __future__ import annotations

from typing import Any

import httpx

from pricewatch.aliases import ModelAliases
from pricewatch.models import PriceRecord


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def collect_new_api(
    provider: dict[str, Any],
    client: httpx.Client,
    aliases: ModelAliases,
    captured_at: str,
) -> list[PriceRecord]:
    base_url = provider["base_url"].rstrip("/")
    pricing_response = client.get(f"{base_url}/api/pricing")
    pricing_response.raise_for_status()
    payload = pricing_response.json()

    status_response = client.get(f"{base_url}/api/status")
    status_response.raise_for_status()
    status = status_response.json().get("data", {})
    quota_per_unit = float(status.get("quota_per_unit") or 500_000)
    currency = str(status.get("quota_display_type") or "USD").upper()
    if currency == "CUSTOM":
        currency = str(status.get("custom_currency_symbol") or "CUSTOM")
    per_million_factor = 1_000_000 / quota_per_unit
    group_ratios = payload.get("group_ratio") or {}

    records: list[PriceRecord] = []
    for model in payload.get("data", []):
        source_model = str(model.get("model_name") or "").strip()
        if not source_model:
            continue
        groups = model.get("enable_groups") or ["default"]
        quota_type = int(model.get("quota_type") or 0)
        model_ratio = _number(model.get("model_ratio")) or 0.0
        completion_ratio = _number(model.get("completion_ratio")) or 1.0
        request_price = _number(model.get("model_price")) if quota_type == 1 else None
        input_price = model_ratio * per_million_factor if quota_type == 0 else None
        output_price = input_price * completion_ratio if input_price is not None else None
        cache_ratio = _number(model.get("cache_ratio"))
        cache_write_ratio = _number(model.get("create_cache_ratio"))
        for group in groups:
            group_ratio = _number(group_ratios.get(group)) or 1.0
            group_input_price = input_price * group_ratio if input_price is not None else None
            records.append(
                PriceRecord(
                    provider_id=provider["id"],
                    provider_name=provider["name"],
                    source_url=provider["pricing_url"],
                    source_model=source_model,
                    canonical_model=aliases.canonicalize(source_model),
                    group=str(group),
                    billing_mode="request" if quota_type == 1 else "token",
                    currency=currency,
                    captured_at=captured_at,
                    input_per_million=group_input_price,
                    output_per_million=(output_price * group_ratio if output_price is not None else None),
                    cache_read_per_million=(group_input_price * cache_ratio if group_input_price is not None and cache_ratio is not None else None),
                    cache_write_per_million=(group_input_price * cache_write_ratio if group_input_price is not None and cache_write_ratio is not None else None),
                    request_price=(request_price * group_ratio if request_price is not None else None),
                    multiplier=group_ratio,
                    condition=str(model.get("billing_expr") or ""),
                    metadata={
                        "pricing_version": model.get("pricing_version"),
                        "billing_mode": model.get("billing_mode"),
                        "model_ratio": model_ratio,
                    },
                )
            )
    return records
