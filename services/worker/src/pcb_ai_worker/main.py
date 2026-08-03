"""Lightweight prototype worker.

Uses a Redis list as a job queue for local development. Replace with a more
durable broker once job volume and retries matter.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("pcb_ai_worker")


def process_job(payload: dict) -> dict:
    job_type = payload.get("type", "unknown")
    if job_type == "verify_design":
        from pcb_ai_circuit_ir.models import Design
        from pcb_ai_verification import run_rules

        design = Design.model_validate(payload["design"])
        findings = run_rules(design)
        return {
            "type": job_type,
            "design_id": design.id,
            "finding_count": len(findings),
            "findings": [f.model_dump(mode="json") for f in findings],
        }
    if job_type == "run_erc":
        return _process_run_erc(payload)
    return {"type": job_type, "status": "ignored"}


def _process_run_erc(payload: dict[str, Any]) -> dict[str, Any]:
    """Async ERC job: parse a report and/or invoke KiCad CLI / Docker.

    Accepted payload keys:
    - ``erc_report``: inline ERC JSON object
    - ``report_path``: filesystem path to ERC JSON/``.rpt`` (offline / mock)
    - ``schematic_path``: ``.kicad_sch`` for live ERC (requires KiCad/Docker)
    - ``mode``: ``auto`` | ``docker`` | ``local`` | ``mock``
    - ``design``: optional Circuit IR for UUID mapping
    """
    from pcb_ai_circuit_ir.models import Design
    from pcb_ai_verification import parse_erc_report, run_schematic_erc

    design = None
    if "design" in payload and payload["design"] is not None:
        design = Design.model_validate(payload["design"])
    elif payload.get("schematic_path") and payload.get("report_path"):
        # Offline path with mapping: ingest schematic without requiring KiCad CLI.
        from pcb_ai_kicad_adapter import ingest_schematic

        design = ingest_schematic(Path(payload["schematic_path"]))
    elif payload.get("schematic_path") and payload.get("erc_report"):
        from pcb_ai_kicad_adapter import ingest_schematic

        design = ingest_schematic(Path(payload["schematic_path"]))

    if "erc_report" in payload and payload["erc_report"] is not None:
        findings = parse_erc_report(payload["erc_report"], design=design)
        return {
            "type": "run_erc",
            "status": "ok",
            "mode": "inline",
            "finding_count": len(findings),
            "findings": [f.model_dump(mode="json") for f in findings],
        }

    report_path = payload.get("report_path")
    schematic_path = payload.get("schematic_path")
    mode = payload.get("mode")

    if report_path and not schematic_path:
        result = run_schematic_erc(report_path=report_path, design=design, mode=mode)
    elif report_path and schematic_path:
        # Prefer prebuilt report (tests / offline) but still map via Design above.
        result = run_schematic_erc(report_path=report_path, design=design, mode=mode)
    elif schematic_path:
        if design is None:
            try:
                from pcb_ai_kicad_adapter import ingest_schematic

                design = ingest_schematic(Path(schematic_path))
            except Exception:
                logger.exception("Failed to ingest schematic for ERC mapping")
        result = run_schematic_erc(
            schematic=schematic_path,
            design=design,
            mode=mode,
            docker_image=payload.get("docker_image"),
        )
    else:
        return {
            "type": "run_erc",
            "status": "error",
            "error": "run_erc requires erc_report, report_path, and/or schematic_path",
        }

    return {
        "type": "run_erc",
        "status": "ok",
        "mode": result.mode,
        "report_path": str(result.report_path) if result.report_path else None,
        "finding_count": len(result.findings),
        "findings": [f.model_dump(mode="json") for f in result.findings],
        "returncode": result.returncode,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    redis_url = os.environ.get("PCB_AI_REDIS_URL", "redis://localhost:6379/0")
    queue_key = os.environ.get("PCB_AI_JOB_QUEUE", "pcb_ai:jobs")

    try:
        import redis
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("redis package required for worker") from exc

    client = redis.Redis.from_url(redis_url, decode_responses=True)
    logger.info("Worker listening on %s (%s)", queue_key, redis_url)

    while True:
        item = client.blpop(queue_key, timeout=5)
        if not item:
            continue
        _, raw = item
        try:
            payload = json.loads(raw)
            result = process_job(payload)
            logger.info("Processed job: %s", result.get("type"))
            client.rpush(f"{queue_key}:results", json.dumps(result))
        except Exception:
            logger.exception("Job failed: %s", raw)
            time.sleep(0.5)


if __name__ == "__main__":
    main()
