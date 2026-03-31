"""Shared helpers for file-based import / pack / export (no dkb_runtime)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_yaml_doc(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for config YAML. Install with: pip install pyyaml"
        )
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def directive_category_from_catalog_entry(entry: dict[str, Any]) -> str | None:
    if entry.get("category"):
        return str(entry["category"])
    meta = entry.get("canonical_meta")
    if isinstance(meta, dict):
        return meta.get("source_category") or meta.get("category")
    return None


def passes_category_filter(doc: dict[str, Any], category: str | None) -> bool:
    exclude = set(doc.get("exclude_categories") or [])
    include = list(doc.get("include_categories") or [])
    if category and category in exclude:
        return False
    if include and category is not None and category not in include:
        return False
    return True


def parse_dimension_storage_key(
    raw_key: str,
    key_to_group: dict[str, str],
) -> tuple[str, str]:
    if "." in raw_key:
        group, dim_key = raw_key.split(".", 1)
        return group, dim_key
    dim_key = raw_key
    group = key_to_group.get(dim_key, "")
    return group, dim_key


def avg_clarity_from_scores(
    scores: dict[str, Any],
    key_to_group: dict[str, str] | None = None,
) -> float:
    ktg = key_to_group or {}
    values: list[float] = []
    for raw_key, payload in scores.items():
        if not isinstance(payload, dict):
            continue
        group, _dim_key = parse_dimension_storage_key(str(raw_key), ktg)
        if group == "clarity":
            try:
                values.append(float(payload.get("score", 0.0)))
            except (TypeError, ValueError):
                continue
    return sum(values) / max(len(values), 1)


def apply_catalog_verdict_dict(vdict: dict[str, Any] | None) -> dict[str, str]:
    if not vdict:
        return {
            "provenance_state": "unknown",
            "trust_state": "reviewing",
            "legal_state": "clear",
            "lifecycle_state": "active",
            "recommendation_state": "candidate",
        }
    return {
        "provenance_state": str(vdict.get("provenance", "unknown")),
        "trust_state": str(vdict.get("trust", "reviewing")),
        "legal_state": str(vdict.get("legal", "clear")),
        "lifecycle_state": str(vdict.get("lifecycle", "active")),
        "recommendation_state": str(vdict.get("recommendation", "candidate")),
    }


def iter_pack_defs(pack_defs: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    packs_raw = pack_defs.get("packs", {})
    if isinstance(packs_raw, dict):
        return [(str(k), v) for k, v in packs_raw.items()]
    if isinstance(packs_raw, list):
        out: list[tuple[str, dict[str, Any]]] = []
        for item in packs_raw:
            if isinstance(item, dict) and "key" in item:
                key = str(item["key"])
                out.append((key, item))
        return out
    return []


def score_value(scores: dict[str, Any], composite_key: str) -> float | None:
    """Return numeric score for a key like clarity.description_clarity."""
    raw = scores.get(composite_key)
    if isinstance(raw, dict):
        try:
            return float(raw.get("score", 0.0))
        except (TypeError, ValueError):
            return None
    return None


def directive_matches_selection(entry: dict[str, Any], selection: dict[str, Any]) -> bool:
    verdict_raw = entry.get("verdict")
    vraw = verdict_raw if isinstance(verdict_raw, dict) else None
    trust = (vraw or {}).get("trust", "reviewing")
    legal = (vraw or {}).get("legal", "clear")
    rec = (vraw or {}).get("recommendation", "candidate")

    ts = selection.get("trust_state")
    if isinstance(ts, list) and trust not in ts:
        return False

    ls = selection.get("legal_state")
    if isinstance(ls, list) and legal not in ls:
        return False

    exclude_rec = selection.get("exclude_recommendation") or []
    if rec in exclude_rec:
        return False

    scores = entry.get("scores") or {}
    if not isinstance(scores, dict):
        scores = {}
    min_scores = selection.get("min_scores") or {}
    if isinstance(min_scores, dict):
        for path, min_val in min_scores.items():
            try:
                threshold = float(min_val)
            except (TypeError, ValueError):
                continue
            val = score_value(scores, str(path))
            if val is None or val < threshold:
                return False

    return True


def catalog_entry_passes_import_filter(
    entry: dict[str, Any],
    doc: dict[str, Any],
) -> bool:
    rules = doc.get("filters", doc)
    min_clarity = float(rules.get("min_clarity_score", 0.3))
    exclude_lifecycle = set(rules.get("exclude_lifecycle", []))

    cat = directive_category_from_catalog_entry(entry)
    if not passes_category_filter(doc, cat):
        return False

    scores = entry.get("scores") or {}
    if not isinstance(scores, dict):
        scores = {}
    if avg_clarity_from_scores(scores) < min_clarity:
        return False

    verdict_raw = entry.get("verdict")
    vfields = apply_catalog_verdict_dict(verdict_raw if isinstance(verdict_raw, dict) else None)
    if vfields["lifecycle_state"] in exclude_lifecycle:
        return False

    return True
