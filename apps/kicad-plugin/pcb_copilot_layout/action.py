"""KiCad PCB editor Action Plugin: layout via local PCB Copilot API."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import api_client, config, dialog
from .paths import (
    PathResolutionError,
    find_schematic,
    project_stem_from_board,
    write_sidecar_pcb,
)

PLUGIN_DIR = Path(__file__).resolve().parent


def _board_filename(board: Any) -> str:
    name = board.GetFileName()
    if callable(name):
        name = name()
    return str(name or "")


def _try_open_sidecar(path: Path) -> str:
    """Best-effort open of the sidecar board; returns a user-facing note."""
    path_str = str(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(path_str)  # type: ignore[attr-defined]
            return (
                f"Asked Windows to open:\n{path_str}\n\n"
                "If a second KiCad window did not appear, use File → Open on that path."
            )
        if sys.platform == "darwin":
            subprocess.Popen(["open", path_str], close_fds=True)
            return f"Asked macOS to open:\n{path_str}"
        subprocess.Popen(["xdg-open", path_str], close_fds=True)
        return f"Asked the desktop to open:\n{path_str}"
    except OSError:
        return (
            f"Sidecar written to:\n{path_str}\n\n"
            "Open it manually in the PCB editor (File → Open)."
        )


def run_layout_action(*, parent: Any = None, board: Any = None) -> None:
    """Core plugin flow (callable from ActionPlugin.Run or tests with fakes)."""
    import pcbnew
    import wx

    if parent is None:
        parent = wx.GetActiveWindow()
    if board is None:
        board = pcbnew.GetBoard()
    if board is None:
        dialog.show_message(
            parent,
            "PCB Copilot",
            "No board is loaded in the PCB editor.",
            error=True,
        )
        return

    board_path_str = _board_filename(board)
    if not board_path_str or board_path_str in {".", "./"}:
        dialog.show_message(
            parent,
            "PCB Copilot",
            "Save the board to disk first so the plugin can resolve the project path.",
            error=True,
        )
        return

    board_path = Path(board_path_str)
    api_base = config.get_api_base(PLUGIN_DIR)
    timeout_s = config.get_timeout_s(PLUGIN_DIR)

    try:
        schematic_path = find_schematic(board_path)
    except PathResolutionError as exc:
        dialog.show_message(parent, "PCB Copilot", str(exc), error=True)
        return

    stem = project_stem_from_board(board_path)
    pcb_name = f"{stem}-copilot.kicad_pcb"

    busy = dialog.show_busy(
        parent,
        f"Requesting layout from {api_base}/v1/layout …",
    )
    try:
        payload = api_client.post_layout(
            api_base,
            schematic_path,
            pcb_name=pcb_name,
            register_proposal=True,
            timeout_s=timeout_s,
        )
    except api_client.ApiError as exc:
        dialog.show_message(parent, "PCB Copilot — API error", str(exc), error=True)
        return
    except OSError as exc:
        dialog.show_message(
            parent,
            "PCB Copilot",
            f"Failed to read schematic {schematic_path}: {exc}",
            error=True,
        )
        return
    finally:
        del busy

    pcb_text = payload.get("pcb_text")
    if not isinstance(pcb_text, str) or not pcb_text.strip():
        dialog.show_message(
            parent,
            "PCB Copilot",
            "Layout response missing pcb_text.",
            error=True,
        )
        return

    choice = dialog.show_summary_dialog(parent, payload)
    proposal_id = str(payload.get("proposal_id") or "")

    if choice == "cancel":
        return

    if choice == "reject":
        if proposal_id:
            api_client.post_decision(
                api_base,
                proposal_id,
                "reject",
                reason="rejected from KiCad action plugin",
            )
        dialog.show_message(
            parent,
            "PCB Copilot",
            "Proposal rejected. Nothing written to disk.",
        )
        return

    try:
        sidecar = write_sidecar_pcb(pcb_text, board_path)
    except (PathResolutionError, OSError) as exc:
        dialog.show_message(
            parent,
            "PCB Copilot",
            f"Failed to write sidecar board:\n{exc}",
            error=True,
        )
        return

    decision_note = ""
    if proposal_id:
        recorded = api_client.post_decision(
            api_base,
            proposal_id,
            "approve",
            reason="approved from KiCad action plugin; sidecar written",
        )
        if recorded is None:
            decision_note = (
                "\n\n(Decision telemetry call failed or was skipped; "
                "sidecar was still written.)"
            )

    open_note = _try_open_sidecar(sidecar)
    dialog.show_message(
        parent,
        "PCB Copilot — Approved",
        f"Wrote sidecar (production board untouched):\n{sidecar}\n\n"
        f"{open_note}{decision_note}",
    )


def register_plugin() -> None:
    """Instantiate and register with pcbnew (call from ``__init__.py``)."""
    import pcbnew

    class PcbCopilotLayoutPlugin(pcbnew.ActionPlugin):
        def defaults(self) -> None:
            self.name = "PCB Copilot — AI Layout"
            self.category = "PCB Copilot"
            self.description = (
                "Upload the project schematic to the local PCB Copilot API, "
                "review the layout proposal, and write a *-copilot.kicad_pcb sidecar."
            )
            self.show_toolbar_button = True
            self.icon_file_name = ""

        def Run(self) -> None:
            run_layout_action()

    PcbCopilotLayoutPlugin().register()
