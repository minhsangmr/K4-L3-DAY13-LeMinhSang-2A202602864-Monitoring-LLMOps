from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Secret and PII patterns
SECRET_PATTERNS = {
    "langfuse_secret_key": re.compile(r"sk-lf-[a-zA-Z0-9_\-]{20,}"),
    "generic_api_key": re.compile(r"(?i)(api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]"),
}

PII_PATTERNS = {
    "raw_cccd": re.compile(r"\b0\d{11}\b"),
    "raw_credit_card": re.compile(r"\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b"),
}

IGNORE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".idea", ".vscode"}
IGNORE_FILES = {".env", "challenge.json", "logs.jsonl", "audit.jsonl"}


def scan_repo() -> int:
    print("=== Scanning repository for Secrets & PII leaks ===")
    violations = []

    for file_path in REPO_ROOT.rglob("*"):
        if not file_path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in file_path.parts):
            continue
        if file_path.name in IGNORE_FILES or file_path.suffix in [".png", ".jpg", ".pyc"]:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel_path = file_path.relative_to(REPO_ROOT)

        # Check secrets
        for name, pattern in SECRET_PATTERNS.items():
            matches = pattern.findall(content)
            if matches:
                violations.append((rel_path, f"Secret detected ({name}): {matches[0][:8]}..."))

        # Check raw unredacted PII in source files (exclude tests/data sample definitions and evidence generators)
        if "tests" not in rel_path.parts and "sample_queries" not in rel_path.name and "evidence" not in rel_path.name:
            for name, pattern in PII_PATTERNS.items():
                # Allow markdown documentation examples if marked with [REDACTED]
                lines = content.splitlines()
                for line_idx, line in enumerate(lines, 1):
                    if "[REDACTED" in line:
                        continue
                    if pattern.search(line):
                        violations.append((rel_path, f"Potential unredacted PII ({name}) at line {line_idx}"))

    if violations:
        print(f"FAILED: Found {len(violations)} potential security violations:")
        for path, msg in violations:
            print(f"  - {path}: {msg}")
        return 1

    print("PASSED: 0 secrets or raw PII leaks detected across repository.")
    return 0


if __name__ == "__main__":
    sys.exit(scan_repo())
