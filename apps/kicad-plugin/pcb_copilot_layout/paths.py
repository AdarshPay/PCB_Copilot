"""Resolve board / project / schematic paths for the layout action.

Never writes production boards; sidecar helper always uses ``*-copilot.kicad_pcb``.
"""

from __future__ import annotations

import json
from pathlib import Path


class PathResolutionError(LookupError):
    """Raised when the plugin cannot locate a required project file."""


def project_stem_from_board(board_path: Path) -> str:
    stem = board_path.stem
    if stem.endswith("-copilot"):
        return stem[: -len("-copilot")]
    return stem


def sidecar_pcb_path(board_path: Path) -> Path:
    """Path for the Copilot layout sidecar next to the open board.

    Never returns the production ``.kicad_pcb`` unless it already *is* a
    ``*-copilot.kicad_pcb`` sidecar (rewriting the sidecar is allowed).
    """
    board_path = board_path.resolve()
    stem = board_path.stem
    if stem.endswith("-copilot"):
        return board_path
    return board_path.with_name(f"{stem}-copilot.kicad_pcb")


def assert_not_production_overwrite(target: Path, production_board: Path) -> None:
    """Refuse writes that would replace the production board file."""
    target_r = target.resolve()
    prod_r = production_board.resolve()
    if target_r == prod_r and not prod_r.stem.endswith("-copilot"):
        raise PathResolutionError(
            f"Refusing to overwrite production board: {prod_r}"
        )
    if target_r.suffix.lower() == ".kicad_pcb" and not target_r.stem.endswith(
        "-copilot"
    ):
        raise PathResolutionError(
            f"Sidecar path must end with '-copilot.kicad_pcb', got: {target_r.name}"
        )


def _schematic_candidates(project_dir: Path, stem: str) -> list[Path]:
    candidates: list[Path] = [
        project_dir / f"{stem}.kicad_sch",
        project_dir / f"{stem}.kicad_sch".replace("-copilot", ""),
    ]
    pro = project_dir / f"{stem}.kicad_pro"
    if not pro.is_file():
        # Any single .kicad_pro in the directory
        pros = sorted(project_dir.glob("*.kicad_pro"))
        if len(pros) == 1:
            pro = pros[0]
    if pro.is_file():
        candidates.insert(0, pro.with_suffix(".kicad_sch"))
        try:
            data = json.loads(pro.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            # KiCad 6+ project JSON occasionally lists sheets / files.
            for key in ("sheets", "files"):
                entries = data.get(key)
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if isinstance(entry, str) and entry.endswith(".kicad_sch"):
                        candidates.append(project_dir / entry)
                    elif isinstance(entry, dict):
                        name = entry.get("file") or entry.get("name")
                        if isinstance(name, str) and name.endswith(".kicad_sch"):
                            candidates.append(project_dir / name)
    # Prefer a uniquely named root schematic if only one exists.
    all_sch = sorted(project_dir.glob("*.kicad_sch"))
    if len(all_sch) == 1:
        candidates.append(all_sch[0])
    return candidates


def find_schematic(board_path: Path, project_dir: Path | None = None) -> Path:
    """Locate the ``.kicad_sch`` associated with the open board/project."""
    board_path = Path(board_path)
    if not board_path.name:
        raise PathResolutionError(
            "Board has no file path — save the PCB to disk first."
        )
    board_path = board_path.resolve()
    project_dir = (project_dir or board_path.parent).resolve()
    stem = project_stem_from_board(board_path)

    seen: set[Path] = set()
    for candidate in _schematic_candidates(project_dir, stem):
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved

    raise PathResolutionError(
        f"No .kicad_sch found next to board {board_path.name} "
        f"in {project_dir} (looked for {stem}.kicad_sch)."
    )


def write_sidecar_pcb(
    pcb_text: str,
    board_path: Path,
    *,
    sidecar: Path | None = None,
) -> Path:
    """Write layout ``pcb_text`` to a ``*-copilot.kicad_pcb`` sidecar only."""
    board_path = Path(board_path).resolve()
    target = Path(sidecar) if sidecar is not None else sidecar_pcb_path(board_path)
    assert_not_production_overwrite(target, board_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(pcb_text, encoding="utf-8", newline="\n")
    return target.resolve()
