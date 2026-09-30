from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))
DEFAULT_RETENTION_DAYS = 90


def record_audit_event(
    action: str,
    target: str,
    actor: str = "operator",
    details: dict[str, Any] | None = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> dict[str, Any]:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()

    entry = {
        "ts": ts,
        "actor": actor,
        "action": action,
        "target": target,
        "details": details or {},
        "retention_days": retention_days,
    }

    # Generate cryptographic checksum for tamper-evident auditing
    serialized = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    entry["checksum"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry
