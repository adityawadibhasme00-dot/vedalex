"""C2 - Fee & concession estimator.

Every figure comes from ``app/knowledge/fee_schedule.json`` (which the ingestion
pipeline also indexes, so the numbers are retrievable and citable) and every
estimate carries the official source URL plus an ``as_of`` date. The service
never invents an amount: an unknown route raises instead of guessing.
"""

from __future__ import annotations

import json
import os
from typing import Any

FEE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "knowledge", "fee_schedule.json"
)

ENTITY_CLASSES = ("individual", "startup", "small_entity", "large_entity")
ROUTES = ("patent", "trademark", "gi", "abs")


def load_schedule() -> dict[str, Any]:
    try:
        with open(FEE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:  # pragma: no cover - packaging issue
        raise RuntimeError(f"fee schedule unavailable: {exc}") from exc


def list_routes() -> list[dict[str, Any]]:
    data = load_schedule()
    return [
        {
            "route": key,
            "label": value.get("label", key),
            "currency": value.get("currency", "INR"),
            "source": data.get("meta", {}).get("sources", {}).get(
                value.get("source_key", ""), ""
            ),
            "note": value.get("note", ""),
        }
        for key, value in data.get("routes", {}).items()
    ]


def entity_multiplier(entity_class: str) -> float:
    data = load_schedule()
    classes = data.get("entity_classes", {})
    entry = classes.get(entity_class)
    if entry is None:
        raise ValueError(f"Unknown entity class: {entity_class}")
    return float(entry.get("multiplier", 1.0))


def estimate(
    route: str,
    entity_class: str = "individual",
    classes: int = 1,
    include_examination: bool = True,
) -> dict[str, Any]:
    """Estimate the official fee total for ``route`` for a given applicant class."""
    if route not in ROUTES:
        raise ValueError(f"Unknown route: {route}")
    if entity_class not in ENTITY_CLASSES:
        raise ValueError(f"Unknown entity class: {entity_class}")
    if classes < 1 or classes > 45:
        raise ValueError("classes must be between 1 and 45")

    data = load_schedule()
    spec = data["routes"][route]
    multiplier = entity_multiplier(entity_class)
    sources = data.get("meta", {}).get("sources", {})
    source_url = sources.get(spec.get("source_key", ""), "")

    line_items: list[dict[str, Any]] = []
    total = 0.0

    if "per_class" in spec:
        amount = round(float(spec["per_class"]) * multiplier, 2)
        total = round(amount * classes, 2)
        line_items.append(
            {
                "name": f"{spec.get('label', route)} x {classes} class(es)",
                "official_amount": float(spec["per_class"]),
                "applied_amount": amount,
            }
        )
    else:
        for item in spec.get("items", []):
            official = float(item.get("amount", 0) or 0)
            if not include_examination and item.get("stage") in {"exam", "grant"}:
                continue
            applied = round(official * multiplier, 2)
            total = round(total + applied, 2)
            line_items.append(
                {
                    "name": item.get("name", ""),
                    "stage": item.get("stage", ""),
                    "official_amount": official,
                    "applied_amount": applied,
                }
            )

    baseline = _baseline_total(spec, classes, include_examination)
    savings = round(max(0.0, baseline - total), 2)

    return {
        "route": route,
        "route_label": spec.get("label", route),
        "entity_class": entity_class,
        "entity_class_label": data["entity_classes"][entity_class]["label"],
        "classes": classes,
        "currency": spec.get("currency", "INR"),
        "line_items": line_items,
        "total": total,
        "baseline_total": baseline,
        "concession_saved": savings,
        "concession_pct": (
            round(100.0 * savings / baseline, 1) if baseline else 0.0
        ),
        "include_examination": include_examination,
        "source_url": source_url,
        "as_of": data.get("meta", {}).get("as_of", ""),
        "disclaimer": data.get("meta", {}).get(
            "note", "Confirm on the official fee schedule before filing."
        ),
        "note": spec.get("note", ""),
    }


def _baseline_total(spec: dict[str, Any], classes: int, include_examination: bool) -> float:
    """Total at full (large-entity / individual) rates - the concession yardstick."""
    if "per_class" in spec:
        return round(float(spec["per_class"]) * classes, 2)
    total = 0.0
    for item in spec.get("items", []):
        if not include_examination and item.get("stage") in {"exam", "grant"}:
            continue
        total += float(item.get("amount", 0) or 0)
    return round(total, 2)
