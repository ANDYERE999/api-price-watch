from __future__ import annotations

import os
from typing import Any

import httpx

from pricewatch.aliases import ModelAliases
from pricewatch.models import PriceRecord


def _per_million(value: Any) -> float | None:
    return float(value) * 1_000_000 if isinstance(value, (int, float)) else None


def collect_sub2api(
    provider: dict[str, Any],
    client: httpx.Client,
    aliases: ModelAliases,
    captured_at: str,
) -> list[PriceRecord]:
    headers: dict[str, str] = {}
    token_env = provider.get("token_env")
    token = os.environ.get(token_env, "") if token_env else ""
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = client.get(
        f"{provider['base_url'].rstrip('/')}/api/v1/model-plaza",
        headers=headers,
    )
    response.raise_for_status()
    body = response.json()
    payload = body.get("data", body)
    records: list[PriceRecord] = []
    for group in payload.get("groups", []):
        group_name = str(group.get("name") or group.get("id") or "default")
        rate = group.get("user_rate_multiplier", group.get("rate_multiplier"))
        for model in group.get("models", []):
            pricing = model.get("pricing") or {}
            source_model = str(model.get("name") or "").strip()
            if not source_model or not pricing:
                continue
            billing_mode = str(pricing.get("billing_mode") or "token")
            intervals = pricing.get("intervals") or []
            variants = intervals if intervals else [pricing]
            for interval in variants:
                condition = ""
                if intervals:
                    minimum = interval.get("min_tokens")
                    maximum = interval.get("max_tokens")
                    condition = f"tokens: {minimum or 0} - {maximum or '∞'}"
                records.append(
                    PriceRecord(
                        provider_id=provider["id"],
                        provider_name=provider["name"],
                        source_url=provider["pricing_url"],
                        source_model=source_model,
                        canonical_model=aliases.canonicalize(source_model),
                        group=group_name,
                        billing_mode=billing_mode,
                        currency="USD",
                        captured_at=captured_at,
                        input_per_million=_per_million(interval.get("input_price")),
                        output_per_million=_per_million(interval.get("output_price")),
                        cache_read_per_million=_per_million(interval.get("cache_read_price")),
                        cache_write_per_million=_per_million(interval.get("cache_write_price")),
                        request_price=pricing.get("per_request_price"),
                        condition=condition,
                        multiplier=float(rate) if isinstance(rate, (int, float)) else None,
                        metadata={
                            "platform": model.get("platform"),
                            "time_pricing": model.get("time_pricing"),
                            "subscription_type": group.get("subscription_type"),
                        },
                    )
                )
    return records
