#!/usr/bin/env python3
"""Export packs as SKILL.md standard format."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from dkb_runtime.core.config import get_settings
from dkb_runtime.models import Pack
from dkb_runtime.services.exporter import export_skill_md


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    output_dir = Path(__file__).resolve().parent.parent / "dist" / "skill-md"

    try:
        packs = db.scalars(select(Pack).where(Pack.status == "active")).all()
        for pack in packs:
            print(f"Exporting: {pack.pack_name}")
            result = export_skill_md(db, pack.pack_id, output_dir / pack.pack_key)
            print(f"  -> {result.file_count} files to {result.output_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
