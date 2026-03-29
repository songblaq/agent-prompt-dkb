# Agent Prompt DKB

## What is this?
A DKB instance for curating and exporting AI agent prompts. Downstream of ai-store-dkb.

## Tech Stack
- Python 3.12+
- Depends on: `dkb-runtime` (from git)
- PostgreSQL 16+ with pgvector

## Setup
```bash
pip install -e ".[dev]"
cp .env.example .env
docker compose up -d postgres
python scripts/import_from_store.py
python scripts/curate.py
python scripts/export_claude_code.py
```

## Project Structure
```
config/
  instance.yml          # Instance metadata (upstream: ai-store-dkb)
  pack_definitions.yml  # 4 curated packs
  export_targets.yml    # 3 export formats
  source_filter.yml     # Import filters from ai-store-dkb
scripts/
  import_from_store.py  # Pull data from ai-store-dkb
  curate.py             # Run curation pipeline
  export_claude_code.py # Export as Claude Code plugins
  export_skill_md.py    # Export as SKILL.md standard
  release.py            # Create versioned release
dist/
  claude-code/          # Claude Code plugin output
  skill-md/             # SKILL.md output
  releases/             # Versioned snapshots
```

## Curated Packs
- Safe Starter: Verified, well-documented basics
- Review Pack: Review-focused skills (function.review >= 0.7)
- Planning Pack: Planning workflows (function.planning >= 0.7)
- Coding Assistant: Coding skills (function.coding >= 0.7)

## Ecosystem
Downstream of ai-store-dkb. Produces user-installable exports.
