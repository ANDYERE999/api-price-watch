from __future__ import annotations

import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from pricewatch.aliases import ModelAliases
from pricewatch.models import PriceRecord


_REFERENCE = re.compile(r"^\$([0-9a-z]+)$")


def _flight_payload(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    chunks: list[str] = []
    for script in soup.find_all("script"):
        text = script.string or ""
        marker = "self.__next_f.push("
        if marker not in text:
            continue
        argument = text[text.index(marker) + len(marker) :]
        if argument.endswith(")"):
            argument = argument[:-1]
        try:
            value = json.loads(argument)
        except json.JSONDecodeError:
            continue
        if isinstance(value, list) and len(value) > 1 and isinstance(value[1], str):
            chunks.append(value[1])
    return "".join(chunks)


def _flight_values(payload: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    starts = list(re.finditer(r"(?m)^([0-9a-z]+):", payload))
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(payload)
        raw = payload[match.end() : end].rstrip("\n")
        try:
            values[match.group(1)] = json.loads(raw)
        except json.JSONDecodeError:
            continue
    return values


def _resolve(value: Any, values: dict[str, Any], seen: set[str] | None = None) -> Any:
    if isinstance(value, str):
        match = _REFERENCE.match(value)
        if match:
            key = match.group(1)
            seen = seen or set()
            if key in seen or key not in values:
                return value
            return _resolve(values[key], values, seen | {key})
        return value
    if isinstance(value, list):
        return [_resolve(item, values, seen) for item in value]
    if isinstance(value, dict):
        return {key: _resolve(item, values, seen) for key, item in value.items()}
    return value


def collect_siliconflow(
    provider: dict[str, Any],
    client: httpx.Client,
    aliases: ModelAliases,
    captured_at: str,
) -> list[PriceRecord]:
    response = client.get(provider["pricing_url"])
    response.raise_for_status()
    values = _flight_values(_flight_payload(response.text))
    records: list[PriceRecord] = []
    seen: set[tuple[str, str, float | None, float | None]] = set()
    for value in values.values():
        if not isinstance(value, dict) or not value.get("modelName"):
            continue
        model = _resolve(value, values)
        prices = model.get("pricing") or []
        if not isinstance(prices, list):
            continue
        price_map: dict[str, float] = {}
        unit = "/ M Tokens"
        for item in prices:
            if not isinstance(item, dict):
                continue
            specification = str(item.get("specification") or "").lower()
            try:
                price_map[specification] = float(item.get("price"))
            except (TypeError, ValueError):
                continue
            unit = str(item.get("unitOfGood") or unit)
        source_model = str(model["modelName"])
        input_price = price_map.get("prompt")
        output_price = price_map.get("completion")
        request_price = next(iter(price_map.values()), None) if "token" not in unit.lower() else None
        key = (source_model, unit, input_price, output_price)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            PriceRecord(
                provider_id=provider["id"],
                provider_name=provider["name"],
                source_url=provider["pricing_url"],
                source_model=source_model,
                canonical_model=aliases.canonicalize(source_model),
                group=str(model.get("mf") or "官方平台"),
                billing_mode="token" if "token" in unit.lower() else "request",
                currency="CNY",
                captured_at=captured_at,
                input_per_million=input_price,
                output_per_million=output_price,
                request_price=request_price,
                condition=unit,
                metadata={"model_id": model.get("modelId")},
            )
        )
    if not records:
        raise ValueError("No SiliconFlow pricing records found in the public page")
    return records
