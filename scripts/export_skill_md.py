"""Export curated packs as SKILL.md standard format."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    output_dir = Path(__file__).parent.parent / "dist" / "skill-md"
    print("agent-prompt-dkb exporter -> SKILL.md")
    print(f"Output: {output_dir}")
    print()
    print("Will generate:")
    print("  dist/skill-md/{name}/SKILL.md")
    print("  dist/skill-md/{name}/resources/")
    print()
    print("TODO: Implement using dkb_runtime.services.exporter")


if __name__ == "__main__":
    main()
