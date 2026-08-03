"""Lightweight prototype worker.

Uses a Redis list as a job queue for local development. Replace with a more
durable broker once job volume and retries matter.
"""

from __future__ import annotations

import json
import logging
import os
import time

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
    return {"type": job_type, "status": "ignored"}


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
