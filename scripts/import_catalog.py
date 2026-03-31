#!/usr/bin/env python3
"""Import directives from catalog.json with source_filter.yml (file only, no database)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from file_pipeline_common import catalog_entry_passes_import_filter, load_yaml_doc, repo_root


def main() -> None:
    root = repo_root()
    default_filter = root / "config" / "source_filter.yml"
    default_out = root / "storage" / "imported" / "directives.json"

    parser = argparse.ArgumentParser(description="Filter catalog.json → directives.json")
    parser.add_argument(
        "--catalog",
        type=Path,
        required=True,
        help="Path to catalog.json (e.g. ai-store-dkb/dist/catalog/catalog.json)",
    )
    parser.add_argument(
        "--filter",
        type=Path,
        default=default_filter,
        help="source_filter.yml path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_out,
        help="Output directives.json path",
    )
    args = parser.parse_args()

    catalog_path: Path = args.catalog
    if not catalog_path.is_file():
        raise SystemExit(f"Catalog not found: {catalog_path}")

    doc = load_yaml_doc(args.filter)
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = raw.get("directives") or []
    if not isinstance(entries, list):
        raise SystemExit("catalog.json must contain a 'directives' array")

    z_total = len(entries)
    included: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if catalog_entry_passes_import_filter(entry, doc):
            included.append(entry)

    x_imported = len(included)
    y_filtered = z_total - x_imported

    out_path: Path = args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "meta": {
            "source_catalog": str(catalog_path.resolve()),
            "filter_config": str(args.filter.resolve()),
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "total_catalog_entries": z_total,
            "imported_count": x_imported,
            "filtered_count": y_filtered,
        },
        "directives": included,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"{x_imported} imported, {y_filtered} filtered, {z_total} total")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
