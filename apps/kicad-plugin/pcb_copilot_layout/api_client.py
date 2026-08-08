"""Minimal HTTP client for the local PCB Copilot API (stdlib only)."""

from __future__ import annotations

import json
import mimetypes
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    """HTTP or protocol failure talking to the local API."""

    def __init__(self, message: str, *, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def _encode_multipart(
    fields: dict[str, str],
    files: dict[str, tuple[str, bytes, str]],
) -> tuple[bytes, str]:
    boundary = f"----PcbCopilot{uuid.uuid4().hex}"
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{boundary}".encode("ascii"))
        lines.append(
            f'Content-Disposition: form-data; name="{name}"'.encode("utf-8")
        )
        lines.append(b"")
        lines.append(str(value).encode("utf-8"))
    for name, (filename, data, content_type) in files.items():
        lines.append(f"--{boundary}".encode("ascii"))
        lines.append(
            (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"'
            ).encode("utf-8")
        )
        lines.append(f"Content-Type: {content_type}".encode("utf-8"))
        lines.append(b"")
        lines.append(data)
    lines.append(f"--{boundary}--".encode("ascii"))
    lines.append(b"")
    body = b"\r\n".join(lines)
    content_type_header = f"multipart/form-data; boundary={boundary}"
    return body, content_type_header


def _request_json(
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout_s: float = 120.0,
) -> Any:
    req_headers = dict(headers or {})
    request = Request(url, data=data, headers=req_headers, method=method)
    try:
        with urlopen(request, timeout=timeout_s) as response:
            raw = response.read()
            status = getattr(response, "status", None) or response.getcode()
    except HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
        raise ApiError(
            f"HTTP {exc.code} from {url}: {err_body or exc.reason}",
            status=exc.code,
            body=err_body,
        ) from exc
    except URLError as exc:
        raise ApiError(
            f"Cannot reach API at {url}: {exc.reason}. "
            "Is uvicorn running on that host/port?"
        ) from exc

    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiError(
            f"Non-JSON response (HTTP {status}) from {url}",
            status=status,
            body=raw.decode("utf-8", errors="replace")[:500],
        ) from exc


def post_layout(
    api_base: str,
    schematic_path: Path,
    *,
    pcb_name: str = "layout.kicad_pcb",
    register_proposal: bool = True,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """``POST /v1/layout`` with multipart schematic upload."""
    schematic_path = Path(schematic_path)
    data = schematic_path.read_bytes()
    mime = mimetypes.guess_type(schematic_path.name)[0] or "application/octet-stream"
    body, content_type = _encode_multipart(
        {
            "pcb_name": pcb_name,
            "register_proposal": "true" if register_proposal else "false",
        },
        {
            "file": (schematic_path.name, data, mime),
        },
    )
    url = f"{api_base.rstrip('/')}/v1/layout"
    result = _request_json(
        "POST",
        url,
        data=body,
        headers={"Content-Type": content_type},
        timeout_s=timeout_s,
    )
    if not isinstance(result, dict):
        raise ApiError("Layout response was not a JSON object")
    return result


def post_decision(
    api_base: str,
    proposal_id: str,
    decision: str,
    *,
    reason: str | None = None,
    timeout_s: float = 30.0,
) -> dict[str, Any] | None:
    """``POST /v1/proposals/{id}/decision`` with approve/reject.

    Returns parsed JSON on success, or ``None`` if the endpoint is unavailable
    (best-effort telemetry; layout sidecar write is independent).
    """
    if decision not in {"approve", "reject"}:
        raise ValueError(f"decision must be approve|reject, got {decision!r}")
    payload: dict[str, Any] = {"decision": decision}
    if reason:
        payload["reason"] = reason
    url = f"{api_base.rstrip('/')}/v1/proposals/{proposal_id}/decision"
    try:
        result = _request_json(
            "POST",
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout_s=timeout_s,
        )
    except ApiError:
        return None
    return result if isinstance(result, dict) else None
