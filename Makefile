.PHONY: setup db-up db-down import curate export-claude export-skill release lint test

setup:
	pip install -e ".[dev]"

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

import:
	python scripts/import_from_store.py

curate:
	python scripts/curate.py

export-claude:
	python scripts/export_claude_code.py

export-skill:
	python scripts/export_skill_md.py

release:
	python scripts/release.py

lint:
	ruff check scripts tests

test:
	pytest -q
