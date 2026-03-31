![CI](https://github.com/songblaq/agent-prompt-dkb/actions/workflows/ci.yml/badge.svg)

# agent-prompt-dkb

AI 에이전트 프롬프트를 큐레이션하여 Claude Code 플러그인 등으로 제공하는 **DKB 인스턴스**.

## What is this?

agent-prompt-dkb는 ai-store-dkb에서 수집된 에이전트 프롬프트 관련 자료를 가져와서 큐레이션하고, 실제 사용 가능한 형태로 export합니다.

## For Users (사용 측)

DKB나 PostgreSQL 없이, export된 결과물만 가져가서 사용할 수 있습니다:

```bash
# dist/claude-code/ 를 자신의 프로젝트에 복사
cp -r dist/claude-code/* ~/.claude/
```

또는 GitHub 릴리즈에서 다운로드하세요.

## For Operators (운영 측)

큐레이션 파이프라인을 직접 운영하려면:

```bash
# Prerequisites: dkb-runtime installed, PostgreSQL running
pip install -e .
cp .env.example .env
docker compose up -d postgres

# Import from ai-store-dkb
python scripts/import_from_store.py

# Run curation pipeline
python scripts/curate.py

# Export
python scripts/export_claude_code.py
python scripts/export_skill_md.py
```

### Auto-update pipeline

When [ai-store-dkb](https://github.com/songblaq/ai-store-dkb) changes, this repo can refresh imports, DB-backed curation, file-based packs, and exports in one go.

**GitHub Actions** (`.github/workflows/auto-update.yml`):

| Trigger | Purpose |
|--------|---------|
| `repository_dispatch` type `catalog-updated` | Upstream (e.g. ai-store-dkb) notifies after catalog publish |
| `workflow_dispatch` | Manual run from the Actions tab |
| Cron `0 9 * * 1` | Weekly check every Monday 09:00 UTC |

The workflow checks out `songblaq/ai-store-dkb`, moves that tree to the **latest GitHub release tag** when one exists (otherwise keeps the default branch), resolves `catalog.json` (under `dist/catalog/` or elsewhere in that tree), runs Alembic + reference seed on an ephemeral Postgres, then: `import_catalog.py` → `import_from_store.py --from-catalog` → `curate.py` → `build_packs.py` → `export_packs.py`. If generated artifacts under `storage/` and `dist/` change, the job commits and pushes (paths are force-added because they are normally gitignored).

**Upstream dispatch** (optional): in ai-store-dkb, call the GitHub API to trigger this repo, for example:

`POST /repos/songblaq/agent-prompt-dkb/dispatches` with body `{"event_type":"catalog-updated","client_payload":{}}` using a token with `contents` access to agent-prompt-dkb.

**Local full pipeline** (after DB is migrated and `schema/02_dkb_seed_reference_v0_1.sql` from dkb-runtime has been applied at least once):

```bash
chmod +x scripts/auto_update.sh
export DATABASE_URL=postgresql+psycopg://dkb:dkb_dev@localhost:5433/agent_prompt_dkb
./scripts/auto_update.sh
```

`CATALOG_PATH` defaults to `storage/tmp/catalog.json`. If that file is missing, the script tries the GitHub Contents API via `gh` (repo `AI_STORE_REPO`, default `songblaq/ai-store-dkb`) or a sibling checkout at `../ai-store-dkb/dist/catalog/catalog.json`.

## Part of DKB Ecosystem

| Repository | Role |
|---|---|
| [directive-knowledge-base](../directive-knowledge-base) | 개념, 명세, 웹 문서 |
| [dkb-runtime](../dkb-runtime) | 설치 가능한 구현체 |
| [ai-store-dkb](../ai-store-dkb) | AI 리서치/수집 스토어 |
| **agent-prompt-dkb** (this) | 에이전트 프롬프트 큐레이션 |

## Curated Packs

| Pack | Description |
|---|---|
| Safe Starter | Verified, well-documented basics |
| Review Pack | Review-focused skills and workflows |
| Planning Pack | Planning-focused workflows |
| Coding Assistant | Coding-focused skills and agents |

## Export Formats

| Format | Path | Description |
|---|---|---|
| Claude Code | `dist/claude-code/` | Plugin format for Claude Code |
| SKILL.md | `dist/skill-md/` | Agent Skills open standard |
| Release | `dist/releases/` | Versioned snapshots |

## License

MIT
