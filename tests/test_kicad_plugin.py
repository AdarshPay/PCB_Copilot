"""Unit tests for KiCad plugin helpers (no pcbnew/wx required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "apps" / "kicad-plugin"
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from pcb_copilot_layout.api_client import _encode_multipart
from pcb_copilot_layout.config import DEFAULT_API_BASE, get_api_base
from pcb_copilot_layout.dialog import format_layout_summary
from pcb_copilot_layout.paths import (
    PathResolutionError,
    find_schematic,
    project_stem_from_board,
    sidecar_pcb_path,
    write_sidecar_pcb,
)

def test_sidecar_never_equals_production(tmp_path: Path) -> None:
    board = tmp_path / "rc_divider.kicad_pcb"
    board.write_text("(kicad_pcb)\n", encoding="utf-8")
    side = sidecar_pcb_path(board)
    assert side.name == "rc_divider-copilot.kicad_pcb"
    assert side != board.resolve()


def test_write_sidecar_refuses_non_copilot_name(tmp_path: Path) -> None:
    board = tmp_path / "prod.kicad_pcb"
    board.write_text("(kicad_pcb)\n", encoding="utf-8")
    with pytest.raises(PathResolutionError, match="must end with"):
        write_sidecar_pcb(
            "(kicad_pcb)\n",
            board,
            sidecar=tmp_path / "evil.kicad_pcb",
        )


def test_write_sidecar_ok(tmp_path: Path) -> None:
    board = tmp_path / "demo.kicad_pcb"
    board.write_text("(kicad_pcb old)\n", encoding="utf-8")
    out = write_sidecar_pcb("(kicad_pcb new)\n", board)
    assert out.name == "demo-copilot.kicad_pcb"
    assert out.read_text(encoding="utf-8").startswith("(kicad_pcb new)")
    assert board.read_text(encoding="utf-8").startswith("(kicad_pcb old)")


def test_find_schematic_same_stem(tmp_path: Path) -> None:
    sch = tmp_path / "demo.kicad_sch"
    sch.write_text("(kicad_sch)\n", encoding="utf-8")
    board = tmp_path / "demo.kicad_pcb"
    board.write_text("(kicad_pcb)\n", encoding="utf-8")
    assert find_schematic(board) == sch.resolve()


def test_find_schematic_from_copilot_board_stem(tmp_path: Path) -> None:
    sch = tmp_path / "demo.kicad_sch"
    sch.write_text("(kicad_sch)\n", encoding="utf-8")
    board = tmp_path / "demo-copilot.kicad_pcb"
    board.write_text("(kicad_pcb)\n", encoding="utf-8")
    assert project_stem_from_board(board) == "demo"
    assert find_schematic(board) == sch.resolve()


def test_format_summary_includes_counts() -> None:
    text = format_layout_summary(
        {
            "proposal_id": "abc",
            "unrouted_nets": ["GND", "VCC"],
            "layout_findings": [{"id": 1}],
            "rule_findings": [],
            "production_mutation": False,
            "human_approval_required": True,
            "metadata": {"placed": 3},
        }
    )
    assert "proposal_id: abc" in text
    assert "unrouted nets: 2" in text
    assert "layout findings: 1" in text
    assert "placed=3" in text


def test_multipart_encoder_roundtrip_shape() -> None:
    body, content_type = _encode_multipart(
        {"pcb_name": "x.kicad_pcb", "register_proposal": "true"},
        {"file": ("a.kicad_sch", b"(kicad_sch)", "application/octet-stream")},
    )
    assert b'name="file"' in body
    assert b"a.kicad_sch" in body
    assert b"(kicad_sch)" in body
    assert content_type.startswith("multipart/form-data; boundary=")


def test_get_api_base_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PCB_COPILOT_API_BASE", "http://127.0.0.1:9000/")
    assert get_api_base(tmp_path) == "http://127.0.0.1:9000"
    monkeypatch.delenv("PCB_COPILOT_API_BASE", raising=False)
    monkeypatch.delenv("PCB_AI_API_BASE", raising=False)
    settings = tmp_path / "pcb_copilot_settings.json"
    settings.write_text(json.dumps({"api_base": "http://127.0.0.1:8001"}), encoding="utf-8")
    assert get_api_base(tmp_path) == "http://127.0.0.1:8001"
    settings.unlink()
    assert get_api_base(tmp_path) == DEFAULT_API_BASE
