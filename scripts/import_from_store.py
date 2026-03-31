#!/usr/bin/env python3
"""Import directive data from ai-store-dkb: shared PostgreSQL (default) or catalog.json file."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import click
import yaml
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from dkb_runtime.core.config import get_settings
from dkb_runtime.models import (
    CanonicalDirective,
    DimensionModel,
    DimensionScore,
    Verdict,
)


def load_source_filter(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def directive_category_from_meta(meta: dict[str, Any] | None) -> str | None:
    if not meta:
        return None
    return meta.get("source_category") or meta.get("category")


def directive_category_from_catalog_entry(entry: dict[str, Any]) -> str | None:
    if entry.get("category"):
        return str(entry["category"])
    meta = entry.get("canonical_meta")
    if isinstance(meta, dict):
        return directive_category_from_meta(meta)
    return None


def passes_category_filter(doc: dict[str, Any], category: str | None) -> bool:
    """Exclude by exclude_categories; if include_categories is set, require known category in list."""
    exclude = set(doc.get("exclude_categories") or [])
    include = list(doc.get("include_categories") or [])
    if category and category in exclude:
        return False
    if include and category is not None and category not in include:
        return False
    return True


def _avg_clarity_from_scores(
    scores: dict[str, Any],
    key_to_group: dict[str, str],
) -> float:
    values: list[float] = []
    for raw_key, payload in scores.items():
        if not isinstance(payload, dict):
            continue
        group, _dim_key = parse_dimension_storage_key(str(raw_key), key_to_group)
        if group == "clarity":
            try:
                values.append(float(payload.get("score", 0.0)))
            except (TypeError, ValueError):
                continue
    return sum(values) / max(len(values), 1)


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


def filter_directives_for_import(
    db: Session, doc: dict[str, Any]
) -> tuple[list[CanonicalDirective], dict[str, int]]:
    """Apply source_filter.yml: category, clarity, lifecycle."""
    rules = doc.get("filters", doc)
    min_clarity = float(rules.get("min_clarity_score", 0.3))
    exclude_lifecycle = set(rules.get("exclude_lifecycle", []))

    stmt = select(CanonicalDirective).where(CanonicalDirective.status == "active")
    directives = list(db.scalars(stmt).all())

    stats = {
        "total_active": len(directives),
        "filtered_category": 0,
        "filtered_clarity": 0,
        "filtered_lifecycle": 0,
        "included": 0,
    }

    included: list[CanonicalDirective] = []
    for d in directives:
        cat = directive_category_from_meta(d.canonical_meta if isinstance(d.canonical_meta, dict) else None)
        if not passes_category_filter(doc, cat):
            stats["filtered_category"] += 1
            continue

        clarity_scores = db.scalars(
            select(DimensionScore)
            .where(DimensionScore.directive_id == d.directive_id)
            .where(DimensionScore.dimension_group == "clarity")
        ).all()

        avg_clarity = sum(s.score for s in clarity_scores) / max(len(clarity_scores), 1)
        if avg_clarity < min_clarity:
            stats["filtered_clarity"] += 1
            continue

        verdict = db.scalars(
            select(Verdict)
            .where(Verdict.directive_id == d.directive_id)
            .order_by(Verdict.evaluated_at.desc())
        ).first()
        if verdict and verdict.lifecycle_state in exclude_lifecycle:
            stats["filtered_lifecycle"] += 1
            continue

        included.append(d)
        stats["included"] += 1

    return included, stats


def _get_dimension_model(db: Session) -> DimensionModel:
    m = db.scalars(
        select(DimensionModel).where(DimensionModel.is_active.is_(True)).order_by(DimensionModel.created_at).limit(1)
    ).first()
    if m is None:
        m = db.scalars(select(DimensionModel).order_by(DimensionModel.created_at).limit(1)).first()
    if m is None:
        raise RuntimeError("No dimension_model row in database; run ai-store / DKB setup before catalog import.")
    return m


def _build_key_to_group(config: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for g in config.get("groups", []):
        name = g.get("name")
        if not name:
            continue
        for d in g.get("dimensions", []):
            out[str(d)] = str(name)
    return out


def _apply_catalog_verdict_dict(vdict: dict[str, Any] | None) -> dict[str, str]:
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


def import_from_catalog(db: Session, catalog_path: Path, doc: dict[str, Any]) -> None:
    rules = doc.get("filters", doc)
    min_clarity = float(rules.get("min_clarity_score", 0.3))
    exclude_lifecycle = set(rules.get("exclude_lifecycle", []))

    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = raw.get("directives") or []
    model = _get_dimension_model(db)
    key_to_group = _build_key_to_group(model.config if isinstance(model.config, dict) else {})

    stats = {
        "total_catalog": len(entries),
        "filtered_category": 0,
        "filtered_clarity": 0,
        "filtered_lifecycle": 0,
        "imported": 0,
    }

    to_upsert: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        cat = directive_category_from_catalog_entry(entry)
        if not passes_category_filter(doc, cat):
            stats["filtered_category"] += 1
            continue

        scores = entry.get("scores") or {}
        if not isinstance(scores, dict):
            scores = {}
        avg_clarity = _avg_clarity_from_scores(scores, key_to_group)
        if avg_clarity < min_clarity:
            stats["filtered_clarity"] += 1
            continue

        verdict_raw = entry.get("verdict")
        vfields = _apply_catalog_verdict_dict(verdict_raw if isinstance(verdict_raw, dict) else None)
        if vfields["lifecycle_state"] in exclude_lifecycle:
            stats["filtered_lifecycle"] += 1
            continue

        to_upsert.append(entry)

    for entry in to_upsert:
        _upsert_directive_from_catalog_entry(db, entry, model, key_to_group)
        stats["imported"] += 1

    db.commit()

    print(f"Catalog file: {catalog_path}")
    print(f"  Entries in catalog: {stats['total_catalog']}")
    print(f"  Filtered (category): {stats['filtered_category']}")
    print(f"  Filtered (clarity < {min_clarity}): {stats['filtered_clarity']}")
    print(f"  Filtered (lifecycle): {stats['filtered_lifecycle']}")
    print(f"  Imported (upserted to local DB): {stats['imported']}")


def _upsert_directive_from_catalog_entry(
    db: Session,
    entry: dict[str, Any],
    model: DimensionModel,
    key_to_group: dict[str, str],
) -> None:
    directive_id = uuid.UUID(str(entry["directive_id"]))
    preferred_name = str(entry.get("preferred_name") or "")
    normalized_summary = entry.get("normalized_summary")
    status = str(entry.get("status") or "active")

    existing = db.get(CanonicalDirective, directive_id)
    entry_meta = entry.get("canonical_meta")
    if isinstance(entry_meta, dict):
        meta = entry_meta
    elif existing is not None:
        em = existing.canonical_meta
        meta = em if isinstance(em, dict) else {}
    else:
        meta = {}

    if existing:
        existing.preferred_name = preferred_name or existing.preferred_name
        existing.normalized_summary = normalized_summary if normalized_summary is not None else existing.normalized_summary
        existing.status = status
        existing.canonical_meta = meta
        canon = existing
    else:
        canon = CanonicalDirective(
            directive_id=directive_id,
            preferred_name=preferred_name or str(directive_id),
            normalized_summary=normalized_summary,
            status=status,
            canonical_meta=meta,
        )
        db.add(canon)
        db.flush()

    db.execute(
        delete(DimensionScore).where(
            DimensionScore.directive_id == directive_id,
            DimensionScore.dimension_model_id == model.dimension_model_id,
        )
    )

    scores = entry.get("scores") or {}
    if isinstance(scores, dict):
        for raw_key, payload in scores.items():
            if not isinstance(payload, dict):
                continue
            group, dim_key = parse_dimension_storage_key(str(raw_key), key_to_group)
            if not group:
                continue
            try:
                score = float(payload.get("score", 0.0))
                confidence = float(payload.get("confidence", 0.5))
            except (TypeError, ValueError):
                continue
            db.add(
                DimensionScore(
                    directive_id=directive_id,
                    dimension_model_id=model.dimension_model_id,
                    dimension_group=group,
                    dimension_key=dim_key,
                    score=score,
                    confidence=confidence,
                    features={"imported_from": "catalog.json"},
                )
            )

    db.execute(delete(Verdict).where(Verdict.directive_id == directive_id))
    vraw = entry.get("verdict")
    vfields = _apply_catalog_verdict_dict(vraw if isinstance(vraw, dict) else None)
    db.add(
        Verdict(
            directive_id=directive_id,
            dimension_model_id=model.dimension_model_id,
            provenance_state=vfields["provenance_state"],
            trust_state=vfields["trust_state"],
            legal_state=vfields["legal_state"],
            lifecycle_state=vfields["lifecycle_state"],
            recommendation_state=vfields["recommendation_state"],
            verdict_reason="imported_from_catalog",
            policy_trace={"source": "import_from_store.py"},
        )
    )


@click.command()
@click.option(
    "--from-catalog",
    "catalog_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Import from ai-store-dkb dist/catalog/catalog.json (upsert into local DB).",
)
@click.option(
    "--from-db",
    "from_db",
    is_flag=True,
    default=False,
    help="Report directives visible after filters using the current database (default when --from-catalog is omitted).",
)
def main(catalog_path: Path | None, from_db: bool) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    filter_path = Path(__file__).resolve().parent.parent / "config" / "source_filter.yml"
    doc = load_source_filter(filter_path)

    try:
        if catalog_path is not None:
            import_from_catalog(db, catalog_path, doc)
        else:
            _included, stats = filter_directives_for_import(db, doc)
            rules = doc.get("filters", doc)
            min_clarity = rules.get("min_clarity_score", 0.3)
            print("Mode: database (read/filter only; no cross-DB sync)")
            print(f"  Active directives: {stats['total_active']}")
            print(f"  Filtered (category): {stats['filtered_category']}")
            print(f"  Filtered (clarity < {min_clarity}): {stats['filtered_clarity']}")
            print(f"  Filtered (lifecycle): {stats['filtered_lifecycle']}")
            print(f"  Included after filters: {stats['included']}")
            if doc.get("include_categories"):
                print(f"  include_categories: {doc['include_categories']}")
            if doc.get("exclude_categories"):
                print(f"  exclude_categories: {doc['exclude_categories']}")
            if from_db:
                print("  Note: --from-db selected (same as default when --from-catalog is omitted).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
