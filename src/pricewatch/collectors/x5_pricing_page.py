from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag

from pricewatch.aliases import ModelAliases
from pricewatch.models import PriceRecord


def _price(text: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(match.group()) if match else None


def _actual_price(cell: Tag | None) -> float | None:
    if cell is None:
        return None
    actual = cell.select_one("strong")
    return _price(actual.get_text(" ", strip=True)) if actual else _price(cell.get_text(" ", strip=True))


def collect_x5_pricing_page(
    provider: dict[str, Any],
    client: httpx.Client,
    aliases: ModelAliases,
    captured_at: str,
) -> list[PriceRecord]:
    response = client.get(provider["pricing_url"])
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    records: list[PriceRecord] = []

    for row in soup.select("tr.token-model[data-model]"):
        source_model = str(row.get("data-model") or "").strip()
        cells = row.select("td")
        title = row.select_one(".token-name")
        condition_node = title.select_one("small") if title else None
        cache_values = cells[2].select(".cache-values > div") if len(cells) > 2 else []
        multiplier = _price(cells[3].get_text(" ", strip=True)) if len(cells) > 3 else None
        records.append(
            PriceRecord(
                provider_id=provider["id"],
                provider_name=provider["name"],
                source_url=provider["pricing_url"],
                source_model=source_model,
                canonical_model=aliases.canonicalize(source_model),
                group="统一分组",
                billing_mode="token",
                currency="CNY",
                captured_at=captured_at,
                input_per_million=_actual_price(cells[0] if cells else None),
                output_per_million=_actual_price(cells[1] if len(cells) > 1 else None),
                cache_read_per_million=_actual_price(cache_values[0] if cache_values else None),
                cache_write_per_million=_actual_price(cache_values[1] if len(cache_values) > 1 else None),
                condition=condition_node.get_text(" ", strip=True) if condition_node else "",
                multiplier=multiplier,
            )
        )

    for row in soup.select("tr.request-table-row"):
        title = row.select_one(".m-name")
        source_model = str(title.get("title") if title else "").strip()
        for cell in row.select("td.request-cost"):
            condition = str(cell.get("data-label") or "")
            records.append(
                PriceRecord(
                    provider_id=provider["id"],
                    provider_name=provider["name"],
                    source_url=provider["pricing_url"],
                    source_model=source_model,
                    canonical_model=aliases.canonicalize(source_model),
                    group=str(row.get("data-provider") or "按次"),
                    billing_mode="request",
                    currency="CNY",
                    captured_at=captured_at,
                    request_price=_price(cell.get_text(" ", strip=True)),
                    condition=condition,
                )
            )
    return records
