"""KiCad S-expression parser smoke tests."""

from __future__ import annotations

import pytest

from pcb_ai_kicad_adapter.parser import ParseError, parse_schematic_sexpr


def test_parse_minimal_sexpr() -> None:
    ast = parse_schematic_sexpr('(kicad_sch (version 20250114) (generator "pcb-ai"))')
    assert ast.head == "kicad_sch"
    assert any(getattr(c, "head", None) == "version" for c in ast.children)


def test_unterminated_raises() -> None:
    with pytest.raises(ParseError):
        parse_schematic_sexpr("(kicad_sch (version 1")
