"""Tests for file-based import/pack pipeline (no dkb_runtime)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_common():
    path = ROOT / "scripts" / "file_pipeline_common.py"
    spec = importlib.util.spec_from_file_location("file_pipeline_common", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_catalog_entry_passes_import_filter_respects_category():
    mod = _load_common()
    doc = {
        "include_categories": ["claude-code"],
        "exclude_categories": ["mcp"],
        "filters": {"min_clarity_score": 0.3, "exclude_lifecycle": []},
    }
    ok = {
        "category": "claude-code",
        "scores": {"clarity.x": {"score": 0.8}},
        "verdict": {"lifecycle": "active"},
    }
    bad_cat = {**ok, "category": "mcp"}
    assert mod.catalog_entry_passes_import_filter(ok, doc)
    assert not mod.catalog_entry_passes_import_filter(bad_cat, doc)


def test_directive_matches_selection_min_scores():
    mod = _load_common()
    sel = {"min_scores": {"function.review": 0.7, "form.workflowness": 0.5}}
    ok = {
        "scores": {
            "function.review": {"score": 0.75},
            "form.workflowness": {"score": 0.55},
        },
        "verdict": {},
    }
    low = {
        "scores": {"function.review": {"score": 0.5}, "form.workflowness": {"score": 0.55}},
        "verdict": {},
    }
    assert mod.directive_matches_selection(ok, sel)
    assert not mod.directive_matches_selection(low, sel)


def test_sample_catalog_roundtrip_counts():
    catalog = ROOT / "storage" / "sample-catalog.json"
    data = json.loads(catalog.read_text(encoding="utf-8"))
    assert len(data["directives"]) == 14
