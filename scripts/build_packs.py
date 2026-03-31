#!/usr/bin/env python3
"""Build pack JSON files from imported directives and pack_definitions.yml (no database)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from file_pipeline_common import directive_matches_selection, iter_pack_defs, load_yaml_doc, repo_root


def main() -> None:
    root = repo_root()
    default_directives = root / "storage" / "imported" / "directives.json"
    default_pack_defs = root / "config" / "pack_definitions.yml"
    default_packs_dir = root / "storage" / "packs"

    parser = argparse.ArgumentParser(description="Build storage/packs/{key}.json from directives")
    parser.add_argument(
        "--directives",
        type=Path,
        default=default_directives,
        help="Path to directives.json from import_catalog.py",
    )
    parser.add_argument(
        "--pack-definitions",
        type=Path,
        default=default_pack_defs,
        help="pack_definitions.yml path",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_packs_dir,
        help="Directory for per-pack JSON files",
    )
    args = parser.parse_args()

    if not args.directives.is_file():
        raise SystemExit(f"Directives file not found: {args.directives}. Run import_catalog.py first.")

    pack_defs = load_yaml_doc(args.pack_definitions)
    pack_list = iter_pack_defs(pack_defs)

    raw = json.loads(args.directives.read_text(encoding="utf-8"))
    directives = raw.get("directives") or []
    if not isinstance(directives, list):
        raise SystemExit("directives.json must contain a 'directives' array")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("\n=== Pack build summary ===")
    for pack_key, pack_def in pack_list:
        selection = pack_def.get("selection") or pack_def.get("selection_policy") or {}
        if not isinstance(selection, dict):
            selection = {}

        matched: list[dict] = []
        for entry in directives:
            if not isinstance(entry, dict):
                continue
            if directive_matches_selection(entry, selection):
                matched.append(entry)

        name = pack_def.get("label") or pack_def.get("name") or pack_key
        goal = pack_def.get("description") or pack_def.get("goal") or ""
        pack_type = pack_def.get("type", "custom")

        out_payload = {
            "pack_key": pack_key,
            "label": name,
            "description": goal,
            "type": pack_type,
            "selection": selection,
            "directive_count": len(matched),
            "directives": matched,
        }

        out_file = args.output_dir / f"{pack_key}.json"
        out_file.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  {pack_key}: {len(matched)} directives → {out_file.name}")

    print(f"\nWrote {len(pack_list)} pack file(s) under {args.output_dir}\n")


if __name__ == "__main__":
    main()
