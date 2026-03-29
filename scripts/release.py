#!/usr/bin/env python3
"""Create a versioned release snapshot."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from dkb_runtime.core.config import get_settings
from dkb_runtime.models import Pack
from dkb_runtime.services.exporter import export_snapshot


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).resolve().parent.parent / "dist" / "releases" / f"v0.1.0_{timestamp}"

    try:
        packs = db.scalars(select(Pack).where(Pack.status == "active")).all()
        for pack in packs:
            print(f"Snapshotting: {pack.pack_name}")
            result = export_snapshot(db, pack.pack_id, output_dir / pack.pack_key)
            print(f"  -> {result.file_count} files to {result.output_path}")

        print(f"\n=== Release created at {output_dir} ===")
    finally:
        db.close()


if __name__ == "__main__":
    main()
