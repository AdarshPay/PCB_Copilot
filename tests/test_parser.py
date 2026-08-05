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


def test_parse_sheet_and_hierarchical_label() -> None:
    src = """
    (kicad_sch
      (version 20250114)
      (uuid "root-uuid")
      (sheet
        (at 0 0)
        (size 10 10)
        (uuid "sheet-uuid")
        (property "Sheetname" "Child")
        (property "Sheetfile" "child.kicad_sch")
        (pin "SIG" input
          (at 0 5 180)
          (uuid "pin-uuid")
        )
      )
      (hierarchical_label "SIG"
        (at 1 5 0)
        (uuid "hlab-uuid")
      )
    )
    """
    ast = parse_schematic_sexpr(src)
    sheet = ast.find("sheet")
    assert sheet is not None
    assert sheet.find("uuid").atom_at(0) == "sheet-uuid"
    assert sheet.find_all("property")[1].atom_at(1) == "child.kicad_sch"
    assert sheet.find("pin").atom_at(0) == "SIG"
    assert ast.find("hierarchical_label").atom_at(0) == "SIG"


def test_parse_bus_and_bus_entry() -> None:
    src = """
    (kicad_sch
      (version 20250114)
      (bus
        (pts (xy 0 0) (xy 10 0))
        (uuid "bus-uuid")
      )
      (bus_entry
        (at 0 5)
        (size 0 -5)
        (uuid "entry-uuid")
      )
      (label "D[1..0]"
        (at 5 0 0)
        (uuid "label-uuid")
      )
    )
    """
    ast = parse_schematic_sexpr(src)
    assert ast.find("bus") is not None
    assert ast.find("bus").find("uuid").atom_at(0) == "bus-uuid"
    entry = ast.find("bus_entry")
    assert entry is not None
    assert entry.find("at").atom_at(0) == "0"
    assert entry.find("size").atom_at(1) == "-5"
    assert ast.find("label").atom_at(0) == "D[1..0]"
