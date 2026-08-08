"""wx dialogs for layout summary approve/reject (KiCad embeds wxPython)."""

from __future__ import annotations

from typing import Any

# wx is provided by KiCad's embedded Python; keep import local for py_compile.
ID_APPROVE = 1001
ID_REJECT = 1002


def _count_findings(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, list):
        return len(value)
    return 0


def format_layout_summary(payload: dict[str, Any]) -> str:
    unrouted = payload.get("unrouted_nets") or []
    if not isinstance(unrouted, list):
        unrouted = []
    proposal_id = payload.get("proposal_id") or "(none)"
    job_id = payload.get("job_id") or ""
    pcb_name = payload.get("pcb_name") or ""
    layout_n = _count_findings(payload, "layout_findings")
    rule_n = _count_findings(payload, "rule_findings")
    lines = [
        "PCB Copilot layout proposal",
        "",
        f"proposal_id: {proposal_id}",
    ]
    if job_id and job_id != proposal_id:
        lines.append(f"job_id: {job_id}")
    if pcb_name:
        lines.append(f"pcb_name: {pcb_name}")
    lines.extend(
        [
            f"unrouted nets: {len(unrouted)}",
            f"layout findings: {layout_n}",
            f"rule findings: {rule_n}",
            f"production_mutation: {payload.get('production_mutation', False)}",
            f"human_approval_required: {payload.get('human_approval_required', True)}",
        ]
    )
    if unrouted:
        preview = ", ".join(str(n) for n in unrouted[:12])
        if len(unrouted) > 12:
            preview += f", … (+{len(unrouted) - 12} more)"
        lines.extend(["", f"Unrouted: {preview}"])
    meta = payload.get("metadata")
    if isinstance(meta, dict) and meta:
        placed = meta.get("placed")
        routed = meta.get("routed") or meta.get("tracks")
        bits = []
        if placed is not None:
            bits.append(f"placed={placed}")
        if routed is not None:
            bits.append(f"routed={routed}")
        if bits:
            lines.extend(["", "metadata: " + ", ".join(bits)])
    lines.extend(
        [
            "",
            "Approve writes a *-copilot.kicad_pcb sidecar (never overwrites production).",
            "Reject discards this proposal.",
        ]
    )
    return "\n".join(lines)


def show_summary_dialog(parent: Any, payload: dict[str, Any]) -> str:
    """Show approve/reject dialog. Returns ``approve``, ``reject``, or ``cancel``."""
    import wx

    summary = format_layout_summary(payload)
    dlg = wx.Dialog(
        parent,
        title="PCB Copilot — Layout proposal",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    text = wx.TextCtrl(
        dlg,
        value=summary,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
    )
    text.SetMinSize((480, 280))
    btn_approve = wx.Button(dlg, ID_APPROVE, "Approve")
    btn_reject = wx.Button(dlg, ID_REJECT, "Reject")
    btn_cancel = wx.Button(dlg, wx.ID_CANCEL, "Cancel")
    btn_approve.SetDefault()

    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_sizer.Add(btn_approve, 0, wx.ALL, 4)
    btn_sizer.Add(btn_reject, 0, wx.ALL, 4)
    btn_sizer.Add(btn_cancel, 0, wx.ALL, 4)

    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(text, 1, wx.EXPAND | wx.ALL, 8)
    root.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
    dlg.SetSizerAndFit(root)
    dlg.CentreOnParent()

    result = "cancel"

    def on_approve(_evt: Any) -> None:
        nonlocal result
        result = "approve"
        dlg.EndModal(ID_APPROVE)

    def on_reject(_evt: Any) -> None:
        nonlocal result
        result = "reject"
        dlg.EndModal(ID_REJECT)

    btn_approve.Bind(wx.EVT_BUTTON, on_approve)
    btn_reject.Bind(wx.EVT_BUTTON, on_reject)

    dlg.ShowModal()
    dlg.Destroy()
    return result


def show_message(parent: Any, title: str, message: str, *, error: bool = False) -> None:
    import wx

    style = wx.OK | (wx.ICON_ERROR if error else wx.ICON_INFORMATION)
    wx.MessageBox(message, title, style=style, parent=parent)


def show_busy(parent: Any, message: str) -> Any:
    """Return a wx.BusyInfo (caller should keep a reference until done)."""
    import wx

    return wx.BusyInfo(message, parent=parent)
