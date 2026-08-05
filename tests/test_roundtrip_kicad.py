"""Round-trip and ingest tests for KiCad schematics."""

from __future__ import annotations

from pathlib import Path

from pcb_ai_kicad_adapter import (
    collect_ast_uuids,
    dump_schematic_sexpr,
    emit_schematic_text,
    ingest_schematic,
    normalize_to_circuit_ir,
    parse_schematic_sexpr,
    semantic_equal,
    uuid_equal,
    uuid_fingerprint,
)
from pcb_ai_kicad_adapter.hierarchy import (
    child_sheet_path,
    expand_bus_members,
    extract_sheet_refs,
)
from pcb_ai_kicad_adapter.parser import SExprNode
from pcb_ai_circuit_ir.models import NetClass
from pcb_ai_verification import run_rules

KICAD_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "kicad"
RC_DIVIDER = KICAD_FIXTURES / "rc_divider.kicad_sch"
HIERARCHY_ROOT = KICAD_FIXTURES / "hierarchy" / "root.kicad_sch"
HIERARCHY_CHILD = KICAD_FIXTURES / "hierarchy" / "child.kicad_sch"
SHARED_ROOT = KICAD_FIXTURES / "shared_sheet" / "root.kicad_sch"
SHARED_CHILD = KICAD_FIXTURES / "shared_sheet" / "child.kicad_sch"
BUS_MEMBERS = KICAD_FIXTURES / "bus" / "bus_members.kicad_sch"
SHEET_UUID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
SHARED_A = "11111111-1111-4111-8111-111111111111"
SHARED_B = "22222222-2222-4222-8222-222222222222"


def _ast_equal(a: SExprNode, b: SExprNode) -> bool:
    if a.is_atom or b.is_atom:
        return a.is_atom and b.is_atom and a.atom == b.atom
    if a.head != b.head or len(a.children) != len(b.children):
        return False
    return all(
        isinstance(x, SExprNode) and isinstance(y, SExprNode) and _ast_equal(x, y)
        for x, y in zip(a.children, b.children, strict=True)
    )


def test_rc_divider_fixture_exists() -> None:
    assert RC_DIVIDER.is_file()


def test_parse_rc_divider_ast() -> None:
    ast = parse_schematic_sexpr(RC_DIVIDER)
    assert ast.head == "kicad_sch"
    assert ast.find("version") is not None
    assert len(ast.find_all("symbol")) >= 3  # R1, R2, GND (+ nested ignored at root)
    assert ast.find("lib_symbols") is not None


def test_ast_serialize_roundtrip_no_semantic_change() -> None:
    original = parse_schematic_sexpr(RC_DIVIDER)
    text = dump_schematic_sexpr(original)
    again = parse_schematic_sexpr(text)
    assert _ast_equal(original, again)


def test_ast_uuid_set_preserved_on_serialize() -> None:
    original = parse_schematic_sexpr(RC_DIVIDER)
    before = collect_ast_uuids(original)
    again = parse_schematic_sexpr(dump_schematic_sexpr(original))
    assert collect_ast_uuids(again) == before
    assert "00000000-0000-4000-8000-000000000001" in before


def test_normalize_rc_divider_components_and_nets() -> None:
    design = ingest_schematic(RC_DIVIDER, design_id="fixture.rc_divider.kicad")
    refs = {c.reference for c in design.components}
    assert {"R1", "R2", "#PWR01"} <= refs

    r1 = next(c for c in design.components if c.reference == "R1")
    assert r1.value == "10k"
    assert r1.symbol_ref == "Device:R"
    assert r1.footprint_ref == "Resistor_SMD:R_0603_1608Metric"
    assert {p.number for p in r1.pins} == {"1", "2"}
    assert r1.source_location is not None
    assert r1.source_location.sheet == "/"
    assert r1.uuid == "00000000-0000-4000-8000-000000000001"

    nets = {n.name: n for n in design.nets}
    assert "VIN" in nets
    assert "MID" in nets
    assert "GND" in nets

    mid_eps = {(e.component_ref, e.pin_number) for e in nets["MID"].endpoints}
    assert mid_eps == {("R1", "2"), ("R2", "1")}

    vin_eps = {(e.component_ref, e.pin_number) for e in nets["VIN"].endpoints}
    assert ("R1", "1") in vin_eps

    gnd_eps = {(e.component_ref, e.pin_number) for e in nets["GND"].endpoints}
    assert ("R2", "2") in gnd_eps
    assert ("#PWR01", "1") in gnd_eps


def test_normalize_then_emit_then_normalize_semantic_equal() -> None:
    first = ingest_schematic(RC_DIVIDER, design_id="fixture.rc_divider.kicad")
    emitted = emit_schematic_text(first)
    second = normalize_to_circuit_ir(
        parse_schematic_sexpr(emitted),
        design_id="fixture.rc_divider.kicad",
    )
    assert semantic_equal(first, second)


def test_component_uuid_roundtrip_via_emit() -> None:
    first = ingest_schematic(RC_DIVIDER, design_id="fixture.rc_divider.kicad")
    second = normalize_to_circuit_ir(
        parse_schematic_sexpr(emit_schematic_text(first)),
        design_id="fixture.rc_divider.kicad",
    )
    assert uuid_equal(first, second, include_nets=True)
    fp = uuid_fingerprint(first)
    assert any(row["uuid"] == "00000000-0000-4000-8000-000000000001" for row in fp["components"])


def test_ingest_runs_deterministic_rules() -> None:
    design = ingest_schematic(RC_DIVIDER)
    findings = run_rules(design)
    # Structural rules should pass on a well-formed divider.
    assert not any(f.rule_id == "struct.unique_references" for f in findings)
    assert not any(f.rule_id == "struct.pin_existence" for f in findings)


def test_cli_ingest(tmp_path: Path) -> None:
    from pcb_ai_kicad_adapter.__main__ import main

    out = tmp_path / "design.json"
    code = main([str(RC_DIVIDER), "-o", str(out), "--rules"])
    assert code == 0
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "R1" in text
    assert "findings" in text


def test_hierarchy_fixtures_exist() -> None:
    assert HIERARCHY_ROOT.is_file()
    assert HIERARCHY_CHILD.is_file()


def test_extract_sheet_refs_from_root() -> None:
    ast = parse_schematic_sexpr(HIERARCHY_ROOT)
    refs = extract_sheet_refs(ast)
    assert len(refs) == 1
    assert refs[0].uuid == SHEET_UUID
    assert refs[0].filename == "child.kicad_sch"
    assert refs[0].pin_names == ["SIG"]
    assert child_sheet_path("/", SHEET_UUID) == f"/{SHEET_UUID}"


def test_hierarchy_ingest_sheet_paths_and_bridge() -> None:
    design = ingest_schematic(HIERARCHY_ROOT, design_id="fixture.hierarchy")
    refs = {c.reference: c for c in design.components}
    assert {"R1", "R2", "#PWR01"} <= set(refs)

    assert refs["R1"].source_location is not None
    assert refs["R1"].source_location.sheet == "/"
    assert refs["R1"].uuid == "00000000-0000-4000-8000-000000000001"

    child_path = f"/{SHEET_UUID}"
    assert refs["R2"].source_location is not None
    assert refs["R2"].source_location.sheet == child_path
    assert refs["R2"].uuid == "00000000-0000-4000-8000-000000000002"
    assert refs["#PWR01"].source_location is not None
    assert refs["#PWR01"].source_location.sheet == child_path

    nets = {n.name: n for n in design.nets}
    assert "VIN" in nets
    assert "SIG" in nets
    assert "GND" in nets

    sig_eps = {(e.component_ref, e.pin_number) for e in nets["SIG"].endpoints}
    assert sig_eps == {("R1", "2"), ("R2", "1")}

    gnd_eps = {(e.component_ref, e.pin_number) for e in nets["GND"].endpoints}
    assert {("R2", "2"), ("#PWR01", "1")} <= gnd_eps

    sheet_paths = {b.description.split("sheet_path=")[-1].split(";")[0] for b in design.blocks}
    assert "/" in sheet_paths
    assert child_path in sheet_paths


def test_hierarchy_child_ast_uuid_roundtrip() -> None:
    original = parse_schematic_sexpr(HIERARCHY_CHILD)
    before = collect_ast_uuids(original)
    again = parse_schematic_sexpr(dump_schematic_sexpr(original))
    assert collect_ast_uuids(again) == before
    assert _ast_equal(original, again)


def test_hierarchy_root_ast_uuid_roundtrip() -> None:
    original = parse_schematic_sexpr(HIERARCHY_ROOT)
    before = set(collect_ast_uuids(original))
    again = parse_schematic_sexpr(dump_schematic_sexpr(original))
    assert set(collect_ast_uuids(again)) == before
    assert SHEET_UUID in before


def test_expand_bus_members_vector_and_group() -> None:
    assert expand_bus_members("D[1..0]") == ["D1", "D0"]
    assert expand_bus_members("DATA[0..2]") == ["DATA0", "DATA1", "DATA2"]
    assert expand_bus_members("{WE OE}") == ["WE", "OE"]
    assert expand_bus_members("MEM{WE OE}") == ["MEMWE", "MEMOE"]
    assert expand_bus_members("SIG") is None


def test_shared_sheet_fixtures_exist() -> None:
    assert SHARED_ROOT.is_file()
    assert SHARED_CHILD.is_file()


def test_shared_sheet_multi_instance_ingest() -> None:
    design = ingest_schematic(SHARED_ROOT, design_id="fixture.shared_sheet")
    refs = {c.reference: c for c in design.components}
    assert {"R1", "R4", "R2", "R3", "#PWR01", "#PWR02"} <= set(refs)

    path_a = f"/{SHARED_A}"
    path_b = f"/{SHARED_B}"
    assert refs["R2"].source_location is not None
    assert refs["R2"].source_location.sheet == path_a
    assert refs["R3"].source_location is not None
    assert refs["R3"].source_location.sheet == path_b
    # Same CAD symbol uuid reused; IR uuids are instance-qualified.
    assert refs["R2"].attributes.get("cad_uuid") == refs["R3"].attributes.get("cad_uuid")
    assert refs["R2"].uuid != refs["R3"].uuid

    sig_nets = [n for n in design.nets if n.name == "SIG"]
    assert len(sig_nets) == 2
    eps_sets = [{(e.component_ref, e.pin_number) for e in n.endpoints} for n in sig_nets]
    assert {("R1", "2"), ("R2", "1")} in eps_sets
    assert {("R4", "2"), ("R3", "1")} in eps_sets

    gnd = next(n for n in design.nets if n.name == "GND")
    gnd_eps = {(e.component_ref, e.pin_number) for e in gnd.endpoints}
    assert {("R2", "2"), ("R3", "2"), ("#PWR01", "1"), ("#PWR02", "1")} <= gnd_eps

    sheet_paths = {b.description.split("sheet_path=")[-1].split(";")[0] for b in design.blocks}
    assert "/" in sheet_paths
    assert path_a in sheet_paths
    assert path_b in sheet_paths


def test_bus_members_fixture_exists() -> None:
    assert BUS_MEMBERS.is_file()


def test_bus_members_not_shorted_and_expanded() -> None:
    design = ingest_schematic(BUS_MEMBERS, design_id="fixture.bus_members")
    nets = {n.name: n for n in design.nets}
    assert "D[1..0]" in nets
    assert nets["D[1..0]"].net_class == NetClass.BUS
    members_c = next(
        c for c in nets["D[1..0]"].constraints if c.name == "bus_members"
    )
    assert members_c.value == ["D1", "D0"]

    assert "D0" in nets and "D1" in nets
    d0_eps = {(e.component_ref, e.pin_number) for e in nets["D0"].endpoints}
    d1_eps = {(e.component_ref, e.pin_number) for e in nets["D1"].endpoints}
    assert d0_eps == {("R1", "1")}
    assert d1_eps == {("R2", "1")}
    # Members must remain electrically separate (bus_entry must not UF-union them).
    assert nets["D0"].uuid != nets["D1"].uuid
    assert not (d0_eps & d1_eps)

    assert any(c.name == "bus" and c.value == "D[1..0]" for c in nets["D0"].constraints)
    assert any(c.name == "bus" and c.value == "D[1..0]" for c in nets["D1"].constraints)


def test_emit_preserves_source_xy_and_sheet_instances() -> None:
    first = ingest_schematic(RC_DIVIDER, design_id="fixture.rc_divider.kicad")
    ast = parse_schematic_sexpr(emit_schematic_text(first))
    r1 = next(
        s
        for s in ast.find_all("symbol")
        if any(
            p.head == "property" and p.atom_at(0) == "Reference" and p.atom_at(1) == "R1"
            for p in s.children
            if hasattr(p, "head")
        )
    )
    at = r1.find("at")
    assert at is not None
    assert float(at.atom_at(0) or 0) == 127.0
    assert float(at.atom_at(1) or 0) == 90.0
    instances = r1.find("instances")
    assert instances is not None
    project = instances.find("project")
    assert project is not None
    assert project.find("path").atom_at(0) == "/"
    sheet_instances = ast.find("sheet_instances")
    assert sheet_instances is not None
    assert any(p.atom_at(0) == "/" for p in sheet_instances.find_all("path"))


def test_bus_ast_roundtrip_preserves_bus_tokens() -> None:
    original = parse_schematic_sexpr(BUS_MEMBERS)
    again = parse_schematic_sexpr(dump_schematic_sexpr(original))
    assert len(again.find_all("bus")) == 1
    assert len(again.find_all("bus_entry")) == 2
    assert _ast_equal(original, again)