from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pricewatch.aliases import ModelAliases  # noqa: E402
from pricewatch.collectors import COLLECTORS  # noqa: E402
from pricewatch.http import create_client  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect model prices from configured providers")
    parser.add_argument("--provider", action="append", help="Only update the selected provider ID")
    parser.add_argument("--strict", action="store_true", help="Fail when any provider fails")
    args = parser.parse_args()

    providers = json.loads((ROOT / "config/providers.json").read_text(encoding="utf-8"))
    selected = set(args.provider or [])
    if selected:
        providers = [provider for provider in providers if provider["id"] in selected]

    now = datetime.now(UTC).replace(microsecond=0)
    captured_at = now.isoformat().replace("+00:00", "Z")
    aliases = ModelAliases(ROOT / "config/model_aliases.json")
    records: list[dict[str, object]] = []
    statuses: list[dict[str, object]] = []

    with create_client() as client:
        for provider in providers:
            try:
                collected = COLLECTORS[provider["type"]](provider, client, aliases, captured_at)
                records.extend(record.as_dict() for record in collected)
                statuses.append({"id": provider["id"], "name": provider["name"], "ok": True, "records": len(collected)})
                print(f"[ok] {provider['name']}: {len(collected)} records")
            except Exception as error:
                statuses.append({"id": provider["id"], "name": provider["name"], "ok": False, "error": str(error)})
                print(f"[error] {provider['name']}: {error}", file=sys.stderr)

    records.sort(key=lambda item: (str(item["canonical_model"]), str(item["provider_id"]), str(item["group"]), str(item["condition"])))
    latest = {"schema_version": 1, "updated_at": captured_at, "providers": statuses, "records": records}
    data_dir = ROOT / "data"
    write_json(data_dir / "latest.json", latest)

    history_path = data_dir / "history.json"
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {"schema_version": 1, "series": {}}
    cutoff = now - timedelta(days=180)
    series = history.setdefault("series", {})
    active_keys: set[str] = set()
    for record in records:
        key = "|".join(
            str(record[field])
            for field in ("provider_id", "canonical_model", "group", "billing_mode", "condition")
        )
        active_keys.add(key)
        points = series.setdefault(
            key,
            {
                "provider_id": record["provider_id"],
                "provider_name": record["provider_name"],
                "canonical_model": record["canonical_model"],
                "source_model": record["source_model"],
                "group": record["group"],
                "billing_mode": record["billing_mode"],
                "currency": record["currency"],
                "condition": record["condition"],
                "points": [],
            },
        )["points"]
        points[:] = [
            point
            for point in points
            if datetime.fromisoformat(point["captured_at"].replace("Z", "+00:00")) >= cutoff
        ]
        price_point = {
            "captured_at": captured_at,
            "input_per_million": record["input_per_million"],
            "output_per_million": record["output_per_million"],
            "cache_read_per_million": record["cache_read_per_million"],
            "cache_write_per_million": record["cache_write_per_million"],
            "request_price": record["request_price"],
        }
        comparable = {key: value for key, value in price_point.items() if key != "captured_at"}
        previous = points[-1] if points else None
        previous_comparable = (
            {key: value for key, value in previous.items() if key != "captured_at"}
            if previous
            else None
        )
        if comparable != previous_comparable:
            points.append(price_point)
    history["updated_at"] = captured_at
    write_json(history_path, history)

    dated_dir = data_dir / "daily" / now.strftime("%Y-%m")
    write_json(dated_dir / f"{now.strftime('%Y-%m-%d')}.json", latest)

    failed = [status for status in statuses if not status["ok"]]
    if not records:
        return 1
    return 1 if args.strict and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
