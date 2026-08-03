"""KiCad S-expression parser smoke tests."""

from __future__ import annotations

import pytest

from pcb_ai_kicad_adapter.parser import ParseError, parse_schematic_sexpr, serialize_sexpr


def test_parse_minimal_sexpr() -> None:
    ast = parse_schematic_sexpr('(kicad_sch (version 20250114) (generator "pcb-ai"))')
    assert ast.head == "kicad_sch"
    assert any(getattr(c, "head", None) == "version" for c in ast.children)


def test_unterminated_raises() -> None:
    with pytest.raises(ParseError):
        parse_schematic_sexpr("(kicad_sch (version 1")


def test_serialize_preserves_atoms_and_nesting() -> None:
    src = '(kicad_sch (version 20250114) (generator "pcb-ai") (uuid "abc"))'
    ast = parse_schematic_sexpr(src)
    text = serialize_sexpr(ast)
    again = parse_schematic_sexpr(text)
    assert again.head == "kicad_sch"
    assert again.find("generator").atom_at(0) == "pcb-ai"
    assert again.find("uuid").atom_at(0) == "abc"


def test_escaped_quotes_in_strings() -> None:
    ast = parse_schematic_sexpr(r'(property "Note" "say \"hi\"")')
    assert ast.atom_at(0) == "Note"
    assert ast.atom_at(1) == 'say "hi"'
