#!/bin/bash
# Full pipeline: fetch catalog (optional), import, DB sync, curate, file packs, export.
# Requires: pip install -e ., PostgreSQL with schema + reference seed (see README).
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CATALOG_PATH="${CATALOG_PATH:-$ROOT/storage/tmp/catalog.json}"
mkdir -p "$(dirname "$CATALOG_PATH")"

if [ ! -f "$CATALOG_PATH" ]; then
  REPO="${AI_STORE_REPO:-songblaq/ai-store-dkb}"
  if command -v gh >/dev/null 2>&1; then
    gh api "repos/${REPO}/contents/dist/catalog/catalog.json" \
      -H "Accept: application/vnd.github.raw" -o "$CATALOG_PATH" || true
  fi
fi
if [ ! -f "$CATALOG_PATH" ]; then
  CANDIDATE="$ROOT/../ai-store-dkb/dist/catalog/catalog.json"
  if [ -f "$CANDIDATE" ]; then
    cp "$CANDIDATE" "$CATALOG_PATH"
  fi
fi
if [ ! -f "$CATALOG_PATH" ]; then
  echo "Missing catalog at $CATALOG_PATH — set CATALOG_PATH, install gh, or clone ai-store-dkb as a sibling repo." >&2
  exit 1
fi

python scripts/import_catalog.py --catalog "$CATALOG_PATH"
python scripts/import_from_store.py --from-catalog "$CATALOG_PATH"
python scripts/curate.py
python scripts/build_packs.py
python scripts/export_packs.py
