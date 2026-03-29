"""Tests for pack definition parsing (curation needs DB + pack_engine)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_curate_module():
    path = ROOT / "scripts" / "curate.py"
    spec = importlib.util.spec_from_file_location("curate", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_iter_pack_defs_dict_shape():
    mod = _load_curate_module()
    raw = {"packs": {"safe-starter": {"label": "Safe", "type": "starter"}}}
    assert mod.iter_pack_defs(raw) == [("safe-starter", {"label": "Safe", "type": "starter"})]


def test_iter_pack_defs_list_shape():
    mod = _load_curate_module()
    raw = {"packs": [{"key": "k", "name": "N", "type": "custom"}]}
    assert mod.iter_pack_defs(raw) == [("k", {"key": "k", "name": "N", "type": "custom"})]


def test_pack_definitions_file_loads():
    mod = _load_curate_module()
    data = mod.load_pack_definitions(ROOT / "config" / "pack_definitions.yml")
    assert "packs" in data
    assert "safe-starter" in data["packs"]
