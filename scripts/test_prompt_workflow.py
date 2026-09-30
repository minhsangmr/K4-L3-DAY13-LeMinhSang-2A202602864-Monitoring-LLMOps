from __future__ import annotations

import os
import time
import httpx
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv(".env")
client = Langfuse()

BASE_URL = "http://127.0.0.1:8000"


def send_chat(request_id: str, message: str = "Explain prompt versioning") -> dict:
    payload = {
        "user_id": "student-prompt",
        "session_id": "session-prompt-test",
        "feature": "qa",
        "message": message,
    }
    r = httpx.post(f"{BASE_URL}/chat", json=payload, headers={"x-request-id": request_id}, timeout=30.0)
    print(f"[{r.status_code}] {request_id} -> {r.headers.get('x-response-time-ms')}ms")
    return r.json()


def main():
    print("--- 1. Testing with Baseline Prompt (v1) ---")
    send_chat("req-v1-baseline", "Explain observability for AI models")

    print("\n--- 2. Promoting Production label to v2 ---")
    client.update_prompt(name="day13-chat", version=2, new_labels=["candidate", "production"])
    p_prod2 = client.get_prompt("day13-chat", label="production")
    print(f"Production label now points to version: {p_prod2.version} (labels: {p_prod2.labels})")

    # Clear prompt cache if client supports it
    if hasattr(client, "clear_prompt_cache"):
        client.clear_prompt_cache()

    print("\n--- 3. Testing with Promoted Production Prompt (v2) ---")
    # Send request after promote
    send_chat("req-v2-promoted", "Explain prompt versioning after promote")

    print("\n--- 4. Rolling back Production label to v1 ---")
    client.update_prompt(name="day13-chat", version=1, new_labels=["baseline", "production"])
    p_prod1 = client.get_prompt("day13-chat", label="production")
    print(f"Production label now points back to version: {p_prod1.version} (labels: {p_prod1.labels})")

    if hasattr(client, "clear_prompt_cache"):
        client.clear_prompt_cache()

    print("\n--- 5. Testing with Rolled-back Production Prompt (v1) ---")
    send_chat("req-v1-rollback", "Explain prompt rollback verification")

    print("\nFlushing Langfuse client events...")
    client.flush()
    time.sleep(5)
    print("Prompt workflow test complete.")


if __name__ == "__main__":
    main()
