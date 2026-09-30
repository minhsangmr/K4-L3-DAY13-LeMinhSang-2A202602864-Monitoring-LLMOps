from __future__ import annotations

import json
from pathlib import Path

from app.audit import record_audit_event
from scripts.query_audit import check_retention, verify_integrity


def test_record_and_verify_audit_log(tmp_path: Path, monkeypatch) -> None:
    test_log = tmp_path / "audit.jsonl"
    monkeypatch.setattr("app.audit.AUDIT_LOG_PATH", test_log)
    monkeypatch.setattr("scripts.query_audit.AUDIT_LOG_PATH", test_log)

    # 1. Record an event
    entry = record_audit_event(
        action="incident_enabled",
        target="rag_slow",
        actor="test-operator",
        details={"reason": "reproduction test"},
        retention_days=30,
    )
    assert entry["action"] == "incident_enabled"
    assert "checksum" in entry
    assert test_log.exists()

    # 2. Verify integrity
    records = [json.loads(line) for line in test_log.read_text(encoding="utf-8").strip().split("\n")]
    valid, tampered = verify_integrity(records)
    assert valid == 1
    assert tampered == 0

    active, expired = check_retention(records)
    assert active == 1
    assert expired == 0

    # 3. Simulate tamper
    records[0]["actor"] = "malicious-hacker"
    valid, tampered = verify_integrity(records)
    assert valid == 0
    assert tampered == 1
