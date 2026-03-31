#!/usr/bin/env python3
"""Export a lightweight pack-summary.json for DKB web UI (comparison + governance)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from file_pipeline_common import (
    directive_matches_selection,
    iter_pack_defs,
    load_yaml_doc,
    repo_root,
)

GROUP_ORDER = ("form", "function", "execution", "governance", "adoption", "clarity")


def _default_directives_path(root: Path) -> Path:
    imported = root / "storage" / "imported" / "directives.json"
    if imported.is_file():
        return imported
    return root / "storage" / "sample-catalog.json"


def _directive_scores_by_group(d: dict[str, Any]) -> dict[str, dict[str, float]]:
    scores = d.get("scores") or {}
    if not isinstance(scores, dict):
        return {g: {} for g in GROUP_ORDER}
    out: dict[str, dict[str, float]] = {g: {} for g in GROUP_ORDER}
    for key, payload in scores.items():
        if not isinstance(payload, dict):
            continue
        try:
            fv = float(payload.get("score", 0.0))
        except (TypeError, ValueError):
            continue
        dg = payload.get("dimension_group")
        if isinstance(dg, str) and dg in out:
            dim_key = str(key).split(".")[-1]
            out[dg][dim_key] = fv
            continue
        k = str(key)
        if "." in k:
            group, dim = k.split(".", 1)
            if group in out:
                out[group][dim] = fv
    return out


def _group_average_for_directive(sb: dict[str, dict[str, float]], group: str) -> float | None:
    g = sb.get(group) or {}
    vals = [v for v in g.values() if isinstance(v, (int, float))]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _pack_avg_scores_by_group(directives: list[dict[str, Any]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for group in GROUP_ORDER:
        avs: list[float] = []
        for d in directives:
            sb = _directive_scores_by_group(d)
            ga = _group_average_for_directive(sb, group)
            if ga is not None:
                avs.append(ga)
        if avs:
            result[group] = sum(avs) / len(avs)
    return result


def _count_verdict_field(directives: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in directives:
        v = d.get("verdict")
        if not isinstance(v, dict):
            val = "unknown"
        else:
            val = str(v.get(field, "unknown"))
        counts[val] = counts.get(val, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))


def _policy_compliance(directives: list[dict[str, Any]]) -> str:
    if not directives:
        return "unknown"
    for d in directives:
        v = d.get("verdict") if isinstance(d.get("verdict"), dict) else {}
        trust = str(v.get("trust", "reviewing"))
        legal = str(v.get("legal", "clear"))
        rec = str(v.get("recommendation", "candidate"))
        if trust == "caution":
            return "caution"
        if legal not in ("clear", "custom"):
            return "caution"
        if rec in ("deprecated", "excluded"):
            return "caution"
    for d in directives:
        v = d.get("verdict") if isinstance(d.get("verdict"), dict) else {}
        if str(v.get("trust", "reviewing")) == "reviewing":
            return "review"
    return "compliant"


def _load_or_build_pack(
    pack_key: str,
    pack_def: dict[str, Any],
    packs_dir: Path,
    directives: list[dict[str, Any]],
) -> dict[str, Any]:
    path = packs_dir / f"{pack_key}.json"
    if path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("directives"):
            return raw
    selection = pack_def.get("selection") or pack_def.get("selection_policy") or {}
    if not isinstance(selection, dict):
        selection = {}
    matched: list[dict[str, Any]] = []
    for entry in directives:
        if isinstance(entry, dict) and directive_matches_selection(entry, selection):
            matched.append(entry)
    name = pack_def.get("label") or pack_def.get("name") or pack_key
    goal = pack_def.get("description") or pack_def.get("goal") or ""
    pack_type = pack_def.get("type", "custom")
    return {
        "pack_key": pack_key,
        "label": name,
        "description": goal,
        "type": pack_type,
        "selection": selection,
        "directive_count": len(matched),
        "directives": matched,
    }


def _summarize_pack(pack: dict[str, Any]) -> dict[str, Any]:
    key = str(pack.get("pack_key", ""))
    directives = pack.get("directives") or []
    if not isinstance(directives, list):
        directives = []
    slim_dirs: list[dict[str, str]] = []
    for d in directives:
        if not isinstance(d, dict):
            continue
        vid = str(d.get("directive_id", ""))
        name = str(d.get("preferred_name") or vid)
        vraw = d.get("verdict") if isinstance(d.get("verdict"), dict) else {}
        trust = str(vraw.get("trust", "reviewing"))
        legal = str(vraw.get("legal", "clear"))
        slim_dirs.append(
            {
                "directive_id": vid,
                "name": name,
                "verdict": trust,
                "verdict_detail": f"{trust} · {legal}",
            }
        )
    dict_rows = [d for d in directives if isinstance(d, dict)]
    return {
        "key": key,
        "label": str(pack.get("label") or key),
        "description": str(pack.get("description") or ""),
        "type": str(pack.get("type") or "custom"),
        "directive_count": int(pack.get("directive_count", len(slim_dirs))),
        "avg_scores_by_group": _pack_avg_scores_by_group(dict_rows),
        "trust_distribution": _count_verdict_field(dict_rows, "trust"),
        "legal_distribution": _count_verdict_field(dict_rows, "legal"),
        "policy_compliance": _policy_compliance(dict_rows),
        "directives": [
            {"name": x["name"], "verdict": x["verdict"], "directive_id": x["directive_id"]} for x in slim_dirs
        ],
    }


def main() -> None:
    root = repo_root()
    parser = argparse.ArgumentParser(description="Write dist/pack-summary.json for DKB UI")
    parser.add_argument(
        "--pack-definitions",
        type=Path,
        default=root / "config" / "pack_definitions.yml",
        help="pack_definitions.yml",
    )
    parser.add_argument(
        "--directives",
        type=Path,
        default=None,
        help="Catalog JSON with directives[] (default: imported or sample-catalog)",
    )
    parser.add_argument(
        "--packs-dir",
        type=Path,
        default=root / "storage" / "packs",
        help="Optional built pack JSON directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "dist" / "pack-summary.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    directives_path = args.directives or _default_directives_path(root)
    if not directives_path.is_file():
        raise SystemExit(f"Directives/catalog not found: {directives_path}")

    pack_defs = load_yaml_doc(args.pack_definitions)
    pack_list = iter_pack_defs(pack_defs)

    raw = json.loads(directives_path.read_text(encoding="utf-8"))
    directives = raw.get("directives") or []
    if not isinstance(directives, list):
        raise SystemExit("Catalog must contain a directives array")

    summaries: list[dict[str, Any]] = []
    for pack_key, pack_def in pack_list:
        built = _load_or_build_pack(pack_key, pack_def, args.packs_dir, directives)
        summaries.append(_summarize_pack(built))

    out_obj = {
        "version": str(pack_defs.get("version", "0.1.0")),
        "source_catalog": str(directives_path.name),
        "packs": summaries,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(summaries)} pack(s) → {args.output}")


if __name__ == "__main__":
    main()
