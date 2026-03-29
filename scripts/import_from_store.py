#!/usr/bin/env python3
"""Import directive data from ai-store-dkb (shared PostgreSQL / DKB schema)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from dkb_runtime.core.config import get_settings
from dkb_runtime.models import CanonicalDirective, DimensionScore, Verdict


def load_source_filter(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def filter_directives_for_import(db: Session, doc: dict[str, Any]) -> list[CanonicalDirective]:
    """Apply clarity and lifecycle rules from config/source_filter.yml."""
    rules = doc.get("filters", doc)
    min_clarity = float(rules.get("min_clarity_score", 0.3))
    exclude_lifecycle = set(rules.get("exclude_lifecycle", []))

    stmt = select(CanonicalDirective).where(CanonicalDirective.status == "active")
    directives = list(db.scalars(stmt).all())

    included: list[CanonicalDirective] = []
    for d in directives:
        clarity_scores = db.scalars(
            select(DimensionScore)
            .where(DimensionScore.directive_id == d.directive_id)
            .where(DimensionScore.dimension_group == "clarity")
        ).all()

        avg_clarity = sum(s.score for s in clarity_scores) / max(len(clarity_scores), 1)
        if avg_clarity < min_clarity:
            continue

        verdict = db.scalars(
            select(Verdict)
            .where(Verdict.directive_id == d.directive_id)
            .order_by(Verdict.evaluated_at.desc())
        ).first()
        if verdict and verdict.lifecycle_state in exclude_lifecycle:
            continue

        included.append(d)

    return included


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    filter_path = Path(__file__).resolve().parent.parent / "config" / "source_filter.yml"
    doc = load_source_filter(filter_path)

    try:
        included = filter_directives_for_import(db, doc)
        rules = doc.get("filters", doc)
        min_clarity = rules.get("min_clarity_score", 0.3)

        directives_total = len(
            db.scalars(select(CanonicalDirective).where(CanonicalDirective.status == "active")).all()
        )
        print(f"Imported {len(included)} directives (filtered from {directives_total})")
        print(f"Filter: min_clarity_score >= {min_clarity}")
        if doc.get("include_categories"):
            print(f"Configured include_categories: {doc['include_categories']} (metadata hook for future use)")
        if doc.get("exclude_categories"):
            print(f"Configured exclude_categories: {doc['exclude_categories']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
