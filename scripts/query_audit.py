"""Audit log query and integrity verification tool (Bonus +5 pts).

Usage:
    python scripts/query_audit.py [--verify] [--filter-action ACTION] [--filter-target TARGET]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

AUDIT_LOG_PATH = Path("data/audit.jsonl")


def load_audit_records() -> list[dict]:
    if not AUDIT_LOG_PATH.exists():
        return []
    records = []
    with AUDIT_LOG_PATH.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                rec["_line"] = line_no
                records.append(rec)
            except json.JSONDecodeError as e:
                print(f"[WARN] Line {line_no} is invalid JSON: {e}", file=sys.stderr)
    return records


def verify_integrity(records: list[dict]) -> tuple[int, int]:
    valid = 0
    tampered = 0
    for rec in records:
        expected_checksum = rec.get("checksum")
        # Recreate the data payload without the checksum field
        payload = {k: v for k, v in rec.items() if k not in ("checksum", "_line")}
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        actual_checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        if actual_checksum == expected_checksum:
            valid += 1
        else:
            tampered += 1
            print(f"[ALERT] Tamper detected on line {rec.get('_line')}! Expected {expected_checksum[:8]}..., got {actual_checksum[:8]}...", file=sys.stderr)
    return valid, tampered


def check_retention(records: list[dict]) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    active = 0
    expired = 0
    for rec in records:
        try:
            ts = datetime.fromisoformat(rec["ts"])
            retention_days = rec.get("retention_days", 90)
            age_days = (now - ts).total_seconds() / 86400.0
            if age_days > retention_days:
                expired += 1
            else:
                active += 1
        except Exception:
            active += 1
    return active, expired


def main() -> int:
    parser = argparse.ArgumentParser(description="Query and verify tamper-evident audit logs.")
    parser.add_argument("--verify", action="store_true", help="Verify SHA-256 checksum integrity of all records.")
    parser.add_argument("--filter-action", help="Filter by action name.")
    parser.add_argument("--filter-target", help="Filter by target name.")
    parser.add_argument("--json", action="store_true", help="Output in raw JSON format.")
    args = parser.parse_args()

    records = load_audit_records()
    print(f"Total audit records found: {len(records)}")

    if not records:
        print("Audit log is currently empty.")
        return 0

    if args.verify:
        valid, tampered = verify_integrity(records)
        active, expired = check_retention(records)
        print(f"Integrity Check: {valid} valid, {tampered} tampered")
        print(f"Retention Check: {active} active, {expired} expired")
        if tampered > 0:
            return 1

    # Filter
    filtered = records
    if args.filter_action:
        filtered = [r for r in filtered if r.get("action") == args.filter_action]
    if args.filter_target:
        filtered = [r for r in filtered if r.get("target") == args.filter_target]

    print(f"\nMatching records ({len(filtered)}):")
    for r in filtered:
        if args.json:
            print(json.dumps({k: v for k, v in r.items() if k != "_line"}, ensure_ascii=False))
        else:
            ts = r.get("ts", "")
            actor = r.get("actor", "")
            action = r.get("action", "")
            target = r.get("target", "")
            chk = r.get("checksum", "")[:8]
            print(f"[{ts}] actor={actor:<12} action={action:<18} target={target:<12} chk={chk}.. details={r.get('details')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
