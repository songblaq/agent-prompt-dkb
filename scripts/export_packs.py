#!/usr/bin/env python3
"""Export pack JSON files to Claude Code, SKILL.md, and token-optimized Markdown layouts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from file_pipeline_common import repo_root


def _directive_title(d: dict, idx: int) -> str:
    name = d.get("preferred_name") or d.get("directive_id") or f"directive-{idx}"
    return str(name)


def _directive_body(d: dict) -> str:
    parts: list[str] = []
    summary = d.get("normalized_summary")
    if summary:
        parts.append(str(summary))
    meta = d.get("canonical_meta")
    if isinstance(meta, dict):
        desc = meta.get("description") or meta.get("summary")
        if desc and str(desc) not in (parts[0] if parts else ""):
            parts.append(str(desc))
    if not parts:
        parts.append("(No summary in catalog entry.)")
    return "\n\n".join(parts)


def export_claude_code_pack(pack: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pack_key = str(pack.get("pack_key", "pack"))
    label = pack.get("label") or pack_key
    description = pack.get("description") or ""
    directives = pack.get("directives") or []

    lines: list[str] = [
        f"# {label}",
        "",
        f"Pack: `{pack_key}`",
        "",
        description,
        "",
        "## How to use",
        "",
        "Apply these directives as project or session guidance. Each section is one curated item from the catalog.",
        "",
    ]

    for i, d in enumerate(directives, start=1):
        if not isinstance(d, dict):
            continue
        title = _directive_title(d, i)
        did = d.get("directive_id", "")
        lines.append(f"## {i}. {title}")
        lines.append("")
        if did:
            lines.append(f"- **id**: `{did}`")
        cat = d.get("category")
        if cat:
            lines.append(f"- **category**: {cat}")
        lines.append("")
        lines.append(_directive_body(d))
        lines.append("")

    (out_dir / "CLAUDE.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def export_skill_md_pack(pack: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pack_key = str(pack.get("pack_key", "pack"))
    label = pack.get("label") or pack_key
    description = pack.get("description") or ""
    directives = pack.get("directives") or []

    trigger = f"curated pack `{pack_key}`"
    lines: list[str] = [
        "---",
        f"name: {label}",
        f"description: {description[:200].replace(chr(10), ' ') if description else trigger}",
        "---",
        "",
        f"# {label}",
        "",
        description,
        "",
        "## When to use",
        "",
        f"Use when you need the **{label}** bundle: {trigger}.",
        "",
        "## Directives",
        "",
    ]

    for i, d in enumerate(directives, start=1):
        if not isinstance(d, dict):
            continue
        title = _directive_title(d, i)
        lines.append(f"### {i}. {title}")
        lines.append("")
        did = d.get("directive_id")
        if did:
            lines.append(f"- **directive_id**: `{did}`")
        lines.append("")
        lines.append(_directive_body(d))
        lines.append("")

    (out_dir / "SKILL.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def export_optimized_pack(pack: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pack_key = str(pack.get("pack_key", "pack"))
    label = pack.get("label") or pack_key
    directives = pack.get("directives") or []

    lines: list[str] = [
        f"# {label}",
        f"key: {pack_key}",
        f"items: {len(directives)}",
        "",
    ]

    for i, d in enumerate(directives, start=1):
        if not isinstance(d, dict):
            continue
        title = _directive_title(d, i)
        did = str(d.get("directive_id", ""))
        cat = d.get("category") or ""
        body = _directive_body(d).replace("\n", " ").strip()
        lines.append(f"## {i}")
        lines.append(f"id: {did}")
        lines.append(f"name: {title}")
        if cat:
            lines.append(f"category: {cat}")
        lines.append(f"text: {body}")
        lines.append("")

    (out_dir / "pack.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    root = repo_root()
    default_packs = root / "storage" / "packs"

    parser = argparse.ArgumentParser(description="Export pack JSON to dist/*")
    parser.add_argument(
        "--packs-dir",
        type=Path,
        default=default_packs,
        help="Directory containing {pack-key}.json files",
    )
    parser.add_argument(
        "--dist-root",
        type=Path,
        default=root / "dist",
        help="dist/ root (creates claude-code, skill-md, optimized)",
    )
    args = parser.parse_args()

    if not args.packs_dir.is_dir():
        raise SystemExit(f"Packs directory not found: {args.packs_dir}. Run build_packs.py first.")

    json_files = sorted(args.packs_dir.glob("*.json"))
    if not json_files:
        raise SystemExit(f"No pack JSON files in {args.packs_dir}")

    cc_root = args.dist_root / "claude-code"
    sk_root = args.dist_root / "skill-md"
    opt_root = args.dist_root / "optimized"

    print("\n=== Export packs ===")
    for path in json_files:
        pack = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(pack, dict):
            continue
        pack_key = str(pack.get("pack_key", path.stem))
        n = pack.get("directive_count", len(pack.get("directives") or []))

        export_claude_code_pack(pack, cc_root / pack_key)
        export_skill_md_pack(pack, sk_root / pack_key)
        export_optimized_pack(pack, opt_root / pack_key)

        print(f"  {pack_key}: {n} directives → claude-code, skill-md, optimized")

    print(f"\nOutputs under {args.dist_root}\n")


if __name__ == "__main__":
    main()
