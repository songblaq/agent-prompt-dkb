"""Tests for import_from_store filtering configuration."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_import_module():
    path = ROOT / "scripts" / "import_from_store.py"
    spec = importlib.util.spec_from_file_location("import_from_store", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_source_filter_yaml_loads():
    mod = _load_import_module()
    doc = mod.load_source_filter(ROOT / "config" / "source_filter.yml")
    assert doc["filters"]["min_clarity_score"] == 0.3
    assert "disappeared" in doc["filters"]["exclude_lifecycle"]
