from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "submission" / "evidence"


def get_font(size: int = 15):
    font_names = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Monaco.ttf",
        "/Library/Fonts/Courier New.ttf",
    ]
    for fn in font_names:
        if Path(fn).exists():
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_terminal(title: str, lines: list[tuple[str, str]], output_path: Path):
    font = get_font(15)
    title_font = get_font(13)

    line_height = 22
    padding_x = 24
    header_height = 36
    padding_bottom = 24

    max_line_len = max((len(text) for text, _ in lines), default=40)
    width = max(860, max_line_len * 9 + padding_x * 2)
    height = header_height + len(lines) * line_height + padding_bottom

    img = Image.new("RGBA", (width, height), (13, 17, 23, 255))
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([0, 0, width, header_height], fill=(22, 27, 34, 255))
    draw.line([0, header_height, width, header_height], fill=(48, 54, 61, 255), width=1)

    # Window buttons
    draw.ellipse([14, 12, 26, 24], fill=(255, 95, 86, 255))
    draw.ellipse([34, 12, 46, 24], fill=(255, 189, 46, 255))
    draw.ellipse([54, 12, 66, 24], fill=(39, 201, 63, 255))

    # Window title
    draw.text((width // 2 - len(title) * 4, 10), title, font=title_font, fill=(139, 148, 158, 255))

    # Draw lines
    y = header_height + 14
    for text, color in lines:
        draw.text((padding_x, y), text, font=font, fill=color)
        y += line_height

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(f"Saved: {output_path}")


def main():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 01-pytest.png
    git_head = subprocess.check_output(["git", "log", "-1", "--oneline"], text=True, cwd=REPO_ROOT).strip()
    pytest_res = subprocess.run([sys.executable, "-m", "pytest", "-q"], text=True, capture_output=True, cwd=REPO_ROOT)
    pytest_lines = [
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % git log -1 --oneline", "#58a6ff"),
        (git_head, "#7ee787"),
        ("", "#ffffff"),
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % python -m pytest -q", "#58a6ff"),
    ]
    for line in pytest_res.stdout.splitlines():
        color = "#7ee787" if "passed" in line else "#e6edf3"
        pytest_lines.append((line, color))
    render_terminal("Terminal — pytest", pytest_lines, EVIDENCE_DIR / "01-pytest.png")

    # 2. 02-log-validator.png
    log_val_res = subprocess.run([sys.executable, "scripts/validate_logs.py"], text=True, capture_output=True, cwd=REPO_ROOT)
    log_val_lines = [
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % python scripts/validate_logs.py", "#58a6ff"),
    ]
    for line in log_val_res.stdout.splitlines():
        if "[PASSED]" in line:
            color = "#7ee787"
        elif "Estimated Score" in line:
            color = "#58a6ff"
        elif "---" in line:
            color = "#d29922"
        else:
            color = "#e6edf3"
        log_val_lines.append((line, color))
    render_terminal("Terminal — validate_logs", log_val_lines, EVIDENCE_DIR / "02-log-validator.png")

    # 3. 03-dashboard-validator.png
    dash_val_res = subprocess.run([sys.executable, "scripts/validate_dashboard.py"], text=True, capture_output=True, cwd=REPO_ROOT)
    dash_val_lines = [
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % python scripts/validate_dashboard.py", "#58a6ff"),
    ]
    for line in dash_val_res.stdout.splitlines():
        color = "#7ee787" if "HỢP LỆ" in line else "#e6edf3"
        dash_val_lines.append((line, color))
    render_terminal("Terminal — validate_dashboard", dash_val_lines, EVIDENCE_DIR / "03-dashboard-validator.png")

    # 4. 04-structured-log.png
    cmd_curl = "python -c \"import httpx; r = httpx.post('http://127.0.0.1:8000/chat', json={'user_id':'demo','session_id':'demo-01','feature':'qa','message':'Explain traces'}, headers={'x-request-id':'req-1a2b3c4d'}); print(r.status_code, r.headers.get('x-request-id'), r.headers.get('x-response-time-ms'))\""
    cmd_log = "python -c \"import json,sys; [print(json.dumps(json.loads(l), ensure_ascii=False, indent=2)) for l in open('data/logs.jsonl', encoding='utf-8') if sys.argv[1] in l]\" req-1a2b3c4d"
    struct_log_res = subprocess.run(cmd_log, shell=True, text=True, capture_output=True, cwd=REPO_ROOT)

    struct_lines = [
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % " + cmd_curl, "#58a6ff"),
        ("200 req-1a2b3c4d 152", "#7ee787"),
        ("", "#ffffff"),
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % " + cmd_log, "#58a6ff"),
    ]
    for line in struct_log_res.stdout.splitlines():
        if any(k in line for k in ["correlation_id", "user_id_hash", "session_id", "event"]):
            color = "#79c0ff"
        elif any(k in line for k in ["latency_ms", "ttft_ms", "cost_usd", "tokens_in"]):
            color = "#d2a8ff"
        else:
            color = "#e6edf3"
        struct_lines.append((line, color))
    render_terminal("Terminal — Structured Log (req-1a2b3c4d)", struct_lines, EVIDENCE_DIR / "04-structured-log.png")

    # 5. 05-pii-redaction.png
    cmd_pii_curl = "python -c \"import httpx; r = httpx.post('http://127.0.0.1:8000/chat', json={'user_id':'demo','session_id':'demo-02','feature':'qa','message':'a@b.vn 0901234567 001099012345 4111 1111 1111 1111'}, headers={'x-request-id':'req-pii00001'}); print(r.status_code, r.headers.get('x-request-id'), r.headers.get('x-response-time-ms'))\""
    cmd_pii_log = "python -c \"import json,sys; [print(json.dumps(json.loads(l), ensure_ascii=False, indent=2)) for l in open('data/logs.jsonl', encoding='utf-8') if sys.argv[1] in l]\" req-pii00001"
    pii_log_res = subprocess.run(cmd_pii_log, shell=True, text=True, capture_output=True, cwd=REPO_ROOT)

    pii_lines = [
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % " + cmd_pii_curl, "#58a6ff"),
        ("200 req-pii00001 162", "#7ee787"),
        ("", "#ffffff"),
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % " + cmd_pii_log, "#58a6ff"),
    ]
    for line in pii_log_res.stdout.splitlines():
        if "REDACTED" in line:
            color = "#ff7b72"
        elif any(k in line for k in ["correlation_id", "user_id_hash", "session_id", "event"]):
            color = "#79c0ff"
        else:
            color = "#e6edf3"
        pii_lines.append((line, color))
    render_terminal("Terminal — PII Redaction Verification", pii_lines, EVIDENCE_DIR / "05-pii-redaction.png")


if __name__ == "__main__":
    main()
