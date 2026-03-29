#!/usr/bin/env python3
"""Run curation pipeline: ensure packs from pack_definitions.yml, then build."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from dkb_runtime.core.config import get_settings
from dkb_runtime.models import Pack
from dkb_runtime.services.pack_engine import build_pack


def load_pack_definitions(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def iter_pack_defs(pack_defs: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    packs_raw = pack_defs.get("packs", {})
    if isinstance(packs_raw, dict):
        return [(str(k), v) for k, v in packs_raw.items()]
    if isinstance(packs_raw, list):
        out = []
        for item in packs_raw:
            key = item["key"]
            out.append((key, item))
        return out
    return []


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    pack_defs_path = Path(__file__).resolve().parent.parent / "config" / "pack_definitions.yml"
    pack_defs = load_pack_definitions(pack_defs_path)

    try:
        for pack_key, pack_def in iter_pack_defs(pack_defs):
            name = pack_def.get("label") or pack_def.get("name") or pack_key
            goal = pack_def.get("description") or pack_def.get("goal") or ""
            pack_type = pack_def.get("type", "custom")
            selection_policy = pack_def.get("selection") or pack_def.get("selection_policy") or {}

            existing = db.scalars(select(Pack).where(Pack.pack_key == pack_key)).first()

            if not existing:
                pack = Pack(
                    pack_key=pack_key,
                    pack_name=name,
                    pack_goal=goal,
                    pack_type=pack_type,
                    selection_policy=selection_policy,
                )
                db.add(pack)
                db.commit()
            else:
                pack = existing

            print(f"\n--- Building pack: {pack.pack_name} ---")
            result = build_pack(db, pack.pack_id)
            print(f"  Items: {result.item_count}, Status: {result.status}")

        print("\n=== Curation complete ===")

    finally:
        db.close()


if __name__ == "__main__":
    main()
