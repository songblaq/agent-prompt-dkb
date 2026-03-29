"""Export curated packs as Claude Code plugin format."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    output_dir = Path(__file__).parent.parent / "dist" / "claude-code"
    print("agent-prompt-dkb exporter -> Claude Code")
    print(f"Output: {output_dir}")
    print()
    print("Will generate:")
    print("  dist/claude-code/agents/*.md")
    print("  dist/claude-code/skills/*.md")
    print("  dist/claude-code/hooks/")
    print("  dist/claude-code/settings.json")
    print()
    print("TODO: Implement using dkb_runtime.services.exporter")


if __name__ == "__main__":
    main()
