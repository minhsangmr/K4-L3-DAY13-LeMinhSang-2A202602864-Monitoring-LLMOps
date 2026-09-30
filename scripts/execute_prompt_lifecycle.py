from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
import httpx
from dotenv import load_dotenv
from langfuse import Langfuse

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"

load_dotenv(ENV_PATH)
client = Langfuse()


def set_env_label(label: str) -> None:
    content = ENV_PATH.read_text(encoding="utf-8")
    content = re.sub(r"LANGFUSE_PROMPT_LABEL=.*", f"LANGFUSE_PROMPT_LABEL={label}", content)
    ENV_PATH.write_text(content, encoding="utf-8")
    print(f"[ENV] Set LANGFUSE_PROMPT_LABEL={label}")


def run_single_request(request_id: str, message: str) -> dict:
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--env-file", ".env"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2.5)  # wait for startup

    try:
        r = httpx.post(
            "http://127.0.0.1:8000/chat",
            json={"user_id": "student-prompts", "session_id": "prompt-lifecycle", "feature": "qa", "message": message},
            headers={"x-request-id": request_id},
            timeout=10.0,
        )
        print(f"Request {request_id}: Status {r.status_code}, correlation_id: {r.headers.get('x-request-id')}")
        return r.json()
    finally:
        proc.terminate()
        proc.wait()
        time.sleep(1)


def main():
    print("=== Step 1: Testing baseline label (v1) ===")
    set_env_label("baseline")
    run_single_request("req-label-baseline-v1", "Explain monitoring in AI apps with baseline prompt")

    print("\n=== Step 2: Testing candidate label (v2) ===")
    set_env_label("candidate")
    run_single_request("req-label-candidate-v2", "Explain monitoring in AI apps with candidate prompt")

    print("\n=== Step 3: Promote production label to v2 ===")
    client.update_prompt(name="day13-chat", version=2, new_labels=["candidate", "production"])
    p_v2 = client.get_prompt("day13-chat", label="production")
    print(f"Promoted! Production prompt version is now: {p_v2.version} (labels: {p_v2.labels})")

    set_env_label("production")
    run_single_request("req-promoted-prod-v2", "Test production after promote to version 2")

    print("\n=== Step 4: Rollback production label to v1 ===")
    client.update_prompt(name="day13-chat", version=1, new_labels=["baseline", "production"])
    p_v1 = client.get_prompt("day13-chat", label="production")
    print(f"Rolled back! Production prompt version is now: {p_v1.version} (labels: {p_v1.labels})")

    run_single_request("req-rollback-prod-v1", "Test production after rollback to version 1")

    print("\nFlushing Langfuse events...")
    client.flush()
    time.sleep(4)
    print("=== All prompt lifecycle steps completed successfully ===")


if __name__ == "__main__":
    main()
