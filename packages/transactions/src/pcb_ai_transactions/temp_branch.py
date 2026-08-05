"""Compile typed operations onto a temporary KiCad schematic branch.

Guardrails
----------
* Never writes the production / source ``.kicad_sch``. Output is always under
  ``dest_dir`` (a temp or review branch directory).
* Human approval is still required before any production CAD write; this module
  only produces a reviewable temporary artifact.
* Emit is connectivity-faithful (synthetic geometry), matching
  ``pcb_ai_kicad_adapter.emit`` — not a lossless layout-preserving rewrite.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pcb_ai_circuit_ir.models import Design, Operation
from pcb_ai_kicad_adapter import ingest_schematic, write_schematic
from pcb_ai_transactions.compiler import TransactionError, apply_operations, export_branch_diff


@dataclass(frozen=True)
class TempBranchResult:
    """Temporary schematic path plus IR branch-diff metadata for review."""

    path: Path
    branch_diff: dict[str, Any]
    before: Design
    after: Design

    @property
    def production_mutation(self) -> bool:
        return False


def compile_temp_branch(
    source_sch: Path | str,
    operations: list[Operation],
    dest_dir: Path | str,
    *,
    branch_name: str = "temp",
    dest_name: str | None = None,
    copy_source_first: bool = True,
) -> TempBranchResult:
    """Ingest ``source_sch``, apply operations on an IR copy, emit to ``dest_dir``.

    Steps
    -----
    1. Resolve paths and refuse to overwrite the production schematic.
    2. Optionally copy the source file into ``dest_dir`` (branch starting point).
    3. Ingest source → ``apply_operations`` on a Design deep-copy → emit
       connectivity-faithful ``.kicad_sch`` to the temp path (overwriting the
       copy when ``copy_source_first`` is True).

    Returns
    -------
    TempBranchResult
        ``path`` is the temp ``.kicad_sch``; ``branch_diff`` includes
        ``production_mutation: False`` and artifact paths for review.

    Human approval is still required before promoting changes to production CAD.
    This function never mutates ``source_sch``.
    """
    source = Path(source_sch).resolve()
    if not source.is_file():
        raise TransactionError(f"Source schematic not found: {source}")
    if source.suffix.lower() != ".kicad_sch":
        raise TransactionError(f"Expected a .kicad_sch source, got {source.name!r}")

    out_dir = Path(dest_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = (out_dir / (dest_name or source.name)).resolve()

    if dest == source:
        raise TransactionError(
            "Refusing to write temp branch onto the production schematic path; "
            "choose a different dest_dir"
        )

    before = ingest_schematic(source)
    after = apply_operations(before, list(operations))

    if copy_source_first:
        shutil.copy2(source, dest)

    write_schematic(after, dest)

    branch_diff = export_branch_diff(
        before, after, operations=list(operations), branch_name=branch_name
    )
    branch_diff = {
        **branch_diff,
        "source_schematic": str(source),
        "temp_schematic": str(dest),
        "human_approval_required": True,
        "emit_mode": "connectivity_faithful",
    }
    return TempBranchResult(path=dest, branch_diff=branch_diff, before=before, after=after)


def emit_design_to_temp(
    design: Design,
    dest: Path | str,
    *,
    source_sch: Path | str | None = None,
) -> Path:
    """Write ``design`` as a temporary ``.kicad_sch`` (no production writes).

    If ``source_sch`` is provided, refuses when ``dest`` resolves to that path.
    Human approval is still required before any production CAD promotion.
    """
    path = Path(dest).resolve()
    if source_sch is not None and path == Path(source_sch).resolve():
        raise TransactionError(
            "Refusing to emit onto the production schematic path; use a temp dest"
        )
    return write_schematic(design, path)
