"""Tests for export scripts (writing dist/ requires DB + exporter service)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_export_claude_code_module_loads():
    mod = _load_script("export_claude_code")
    assert callable(mod.main)


def test_export_skill_md_module_loads():
    mod = _load_script("export_skill_md")
    assert callable(mod.main)


def test_release_module_loads():
    mod = _load_script("release")
    assert callable(mod.main)
