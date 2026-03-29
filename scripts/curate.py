"""Run curation pipeline: import -> canonicalize -> score -> verdict -> pack."""

from __future__ import annotations


def main() -> None:
    print("agent-prompt-dkb curation pipeline")
    print()
    print("Steps:")
    print("  1. Import from ai-store-dkb")
    print("  2. Additional canonicalization")
    print("  3. Prompt-specific scoring")
    print("  4. Generate verdicts")
    print("  5. Build curated packs")
    print()
    print("TODO: Implement using dkb_runtime services")


if __name__ == "__main__":
    main()
