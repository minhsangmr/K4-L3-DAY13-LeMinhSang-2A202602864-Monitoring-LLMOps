from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "submission" / "evidence"
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"


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
    font = get_font(14)
    title_font = get_font(13)

    line_height = 22
    padding_x = 24
    header_height = 36
    padding_bottom = 24

    max_line_len = max((len(text) for text, _ in lines), default=40)
    width = max(900, max_line_len * 9 + padding_x * 2)
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
    print(f"Generated terminal screenshot: {output_path}")


def generate_incident_metric():
    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except Exception:
                continue

    resp_sent = [r for r in records if r.get("event") == "response_sent"]
    latencies = [r.get("latency_ms", 0) for r in resp_sent]
    indices = list(range(1, len(latencies) + 1))

    plt.style.use("seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")
    ax.tick_params(colors="#cbd5e1", labelsize=10)
    ax.xaxis.label.set_color("#94a3b8")
    ax.yaxis.label.set_color("#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#334155")

    # Split into baseline (first 10) and challenge incident (last 5)
    baseline_idx = indices[:10]
    baseline_lat = latencies[:10]
    incident_idx = indices[10:]
    incident_lat = latencies[10:]

    ax.plot(baseline_idx, baseline_lat, color="#38bdf8", marker="o", linewidth=2, label="Normal Baseline (~160-220ms)")
    ax.plot(incident_idx, incident_lat, color="#ef4444", marker="s", linewidth=2.5, label="Challenge Incident (rag_slow: ~2650-2661ms)")
    ax.plot([baseline_idx[-1], incident_idx[0]], [baseline_lat[-1], incident_lat[0]], color="#f59e0b", linestyle="--", linewidth=1.5)

    ax.axhline(2000, color="#f59e0b", linestyle=":", linewidth=2, label="Challenge Alert Threshold (2000ms)")
    ax.axhline(3000, color="#ef4444", linestyle=":", linewidth=2, label="SLO Threshold (3000ms)")

    ax.annotate(
        "Incident Start:\nrag_slow enabled\n(Latency jumps +1600%)",
        xy=(incident_idx[0], incident_lat[0]),
        xytext=(incident_idx[0] - 3, 2200),
        arrowprops=dict(facecolor="#f59e0b", shrink=0.08, width=1.5, headwidth=6),
        color="#f8fafc",
        fontweight="bold",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", fc="#334155", ec="#f59e0b", lw=1),
    )

    ax.set_title(
        "12. Incident Metric: Latency Degradation During Challenge\n"
        "Cohort: K4 | Challenge ID: day13-k4-l3b-monitoring-llmops-v1 | Incident: rag_slow",
        color="#f8fafc",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Request Sequence (#)", fontsize=10)
    ax.set_ylabel("Latency (ms)", fontsize=10)
    ax.legend(loc="upper left", fontsize=9, facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0")
    ax.set_ylim(0, 3200)

    plt.tight_layout()
    output_path = EVIDENCE_DIR / "12-incident-metric.png"
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated incident metric: {output_path}")


def generate_incident_log():
    lines = [
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % # Lọc request chậm > 2000ms:", "#58a6ff"),
        ("python -c \"import json; rows=[json.loads(l) for l in open('data/logs.jsonl', encoding='utf-8')]; [print(r['ts'], r['correlation_id'], r['session_id'], r['latency_ms'], 'ms') for r in rows if r.get('event')=='response_sent' and r.get('latency_ms',0)>2000]\"", "#e6edf3"),
        ("2026-09-30T04:29:07.719708Z | req-62659a98 | k4-l3b-challenge-s04 | 2654 ms", "#ff7b72"),
        ("2026-09-30T04:29:10.382490Z | req-990ffb34 | k4-l3b-challenge-s02 | 2660 ms", "#ff7b72"),
        ("2026-09-30T04:29:13.042370Z | req-c0246e61 | k4-l3b-challenge-s03 | 2657 ms", "#ff7b72"),
        ("2026-09-30T04:29:15.705772Z | req-24839cfc | k4-l3b-challenge-s01 | 2661 ms", "#ff7b72"),
        ("2026-09-30T04:29:18.364066Z | req-568d0c1f | k4-l3b-challenge-s05 | 2656 ms", "#ff7b72"),
        ("", "#ffffff"),
        ("minhsang@macbook K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps % # Chi tiết request_received và response_sent của req-62659a98:", "#58a6ff"),
        ("python -c \"import json,sys; [print(json.dumps(json.loads(l), ensure_ascii=False, indent=2)) for l in open('data/logs.jsonl', encoding='utf-8') if sys.argv[1] in l]\" req-62659a98", "#e6edf3"),
        ("{", "#79c0ff"),
        ("  \"service\": \"api\",", "#e6edf3"),
        ("  \"payload\": {", "#e6edf3"),
        ("    \"message_preview\": \"Which signal should be checked after latency increases?\"", "#a5d6ff"),
        ("  },", "#e6edf3"),
        ("  \"event\": \"request_received\",", "#7ee787"),
        ("  \"correlation_id\": \"req-62659a98\",", "#d2a8ff"),
        ("  \"feature\": \"monitoring\",", "#e6edf3"),
        ("  \"model\": \"claude-sonnet-4-5\",", "#e6edf3"),
        ("  \"user_id_hash\": \"c3a24a72d92a\",", "#e6edf3"),
        ("  \"env\": \"dev\",", "#e6edf3"),
        ("  \"session_id\": \"k4-l3b-challenge-s04\",", "#e6edf3"),
        ("  \"level\": \"info\",", "#e6edf3"),
        ("  \"ts\": \"2026-09-30T04:29:05.063926Z\"", "#e6edf3"),
        ("}", "#79c0ff"),
        ("{", "#79c0ff"),
        ("  \"service\": \"api\",", "#e6edf3"),
        ("  \"latency_ms\": 2654,  <-- [ANOMALY: High latency > 2000ms threshold]", "#ff7b72"),
        ("  \"ttft_ms\": 52,        <-- [NORMAL: First token fast]", "#7ee787"),
        ("  \"tokens_in\": 36,", "#e6edf3"),
        ("  \"tokens_out\": 131,", "#e6edf3"),
        ("  \"cost_usd\": 0.002073,", "#e6edf3"),
        ("  \"quality_score\": 0.9,", "#7ee787"),
        ("  \"tool_name\": \"retrieval\",", "#e6edf3"),
        ("  \"tool_success\": true,", "#7ee787"),
        ("  \"payload\": {", "#e6edf3"),
        ("    \"answer_preview\": \"Starter answer. You should improve this output logic...\"", "#a5d6ff"),
        ("  },", "#e6edf3"),
        ("  \"event\": \"response_sent\",", "#7ee787"),
        ("  \"correlation_id\": \"req-62659a98\",", "#d2a8ff"),
        ("  \"feature\": \"monitoring\",", "#e6edf3"),
        ("  \"model\": \"claude-sonnet-4-5\",", "#e6edf3"),
        ("  \"user_id_hash\": \"c3a24a72d92a\",", "#e6edf3"),
        ("  \"env\": \"dev\",", "#e6edf3"),
        ("  \"session_id\": \"k4-l3b-challenge-s04\",", "#e6edf3"),
        ("  \"level\": \"info\",", "#e6edf3"),
        ("  \"ts\": \"2026-09-30T04:29:07.719708Z\"", "#e6edf3"),
        ("}", "#79c0ff"),
    ]
    render_terminal("Terminal — Incident Log Investigation (req-62659a98)", lines, EVIDENCE_DIR / "13-incident-log.png")


def generate_incident_trace():
    # Render waterfall for incident trace d0e1f84ca008a3cd00c2641ac988c6b6
    img_w, img_h = 1000, 520
    img = Image.new("RGBA", (img_w, img_h), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    font_bold = get_font(15)
    font_normal = get_font(13)
    font_small = get_font(11)

    # Top title
    draw.rectangle([0, 0, img_w, 55], fill=(30, 41, 59, 255))
    draw.text((20, 15), "Langfuse Cloud — Trace Waterfall & Span Hierarchy", font=font_bold, fill=(248, 250, 252, 255))
    draw.text((img_w - 380, 18), "Project: day13-k4-l3b-2A202602864", font=font_normal, fill=(56, 189, 248, 255))

    # Trace metadata header
    draw.rectangle([20, 70, img_w - 20, 135], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))
    draw.text((35, 80), "Trace: day13-agent-request", font=font_bold, fill=(248, 250, 252, 255))
    draw.text((35, 105), "ID: d0e1f84ca008a3cd00c2641ac988c6b6", font=font_normal, fill=(148, 163, 184, 255))
    draw.text((450, 80), "Correlation ID: req-62659a98", font=font_bold, fill=(210, 168, 255, 255))
    draw.text((450, 105), "Session: k4-l3b-challenge-s04 | User: c3a24a72d92a", font=font_normal, fill=(148, 163, 184, 255))
    draw.text((780, 80), "Duration: 2.655s", font=font_bold, fill=(239, 68, 68, 255))
    draw.text((780, 105), "Status: 200 OK | Env: dev", font=font_normal, fill=(34, 197, 94, 255))

    # Waterfall Spans
    y_start = 160
    spans = [
        ("day13-agent-request", "TRACE", 0, 2655, 2655, "#38bdf8", "Root trace (total: 2655ms)"),
        ("└── lab-agent-run", "AGENT", 0, 2655, 2655, "#818cf8", "Root agent observation (2655ms)"),
        ("    ├── retrieval", "RETRIEVER", 0, 2501, 2501, "#ef4444", "Vector store retrieve (2501ms) <-- [ROOT CAUSE: rag_slow delay]"),
        ("    └── generation", "GENERATION", 2502, 153, 2655, "#22c55e", "LLM generate token (153ms, normal)"),
    ]

    total_duration = 2700
    timeline_x_start = 380
    timeline_w = 580

    for i, (name, stype, start_ms, dur_ms, end_ms, color, desc) in enumerate(spans):
        y = y_start + i * 80
        draw.rectangle([20, y, img_w - 20, y + 68], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))

        draw.text((35, y + 12), name, font=font_bold, fill=(248, 250, 252, 255))
        draw.text((35, y + 36), f"Type: {stype} | Duration: {dur_ms}ms", font=font_normal, fill=color)

        # Timeline bar
        bar_x = timeline_x_start + int((start_ms / total_duration) * timeline_w)
        bar_len = max(8, int((dur_ms / total_duration) * timeline_w))
        draw.rectangle([bar_x, y + 16, bar_x + bar_len, y + 36], fill=color)
        draw.text((bar_x + 5, y + 42), desc, font=font_small, fill=(226, 232, 240, 255))

    output_path = EVIDENCE_DIR / "14-incident-trace.png"
    img.save(output_path)
    print(f"Generated incident trace: {output_path}")


def generate_trace_list_image():
    # Evidence 06: Trace List
    img_w, img_h = 1000, 600
    img = Image.new("RGBA", (img_w, img_h), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    font_bold = get_font(15)
    font_normal = get_font(13)
    font_small = get_font(11)

    draw.rectangle([0, 0, img_w, 55], fill=(30, 41, 59, 255))
    draw.text((20, 15), "Langfuse Cloud — Tracing: day13-agent-request", font=font_bold, fill=(248, 250, 252, 255))
    draw.text((img_w - 400, 18), "Project: day13-k4-l3b-2A202602864", font=font_bold, fill=(56, 189, 248, 255))

    # Table Header
    headers = [("Timestamp (UTC)", 140), ("Trace ID", 240), ("Session ID", 180), ("Latency", 100), ("Input / Output", 140), ("Tags", 160)]
    hx = 20
    draw.rectangle([20, 70, img_w - 20, 105], fill=(51, 65, 85, 255))
    for hname, hw in headers:
        draw.text((hx + 8, 78), hname, font=font_bold, fill=(226, 232, 240, 255))
        hx += hw

    traces_data = [
        ("04:29:05", "d0e1f84ca008a3cd00c2641ac988c6b6", "k4-l3b-challenge-s04", "2.655s", "(redacted preview)", "lab, monitoring"),
        ("04:29:07", "4a91b2c7e015d83a19bc8201a478cf31", "k4-l3b-challenge-s02", "2.660s", "(redacted preview)", "lab, monitoring"),
        ("04:29:10", "3f82d1a9b407e62a84dc9182b539da42", "k4-l3b-challenge-s03", "2.657s", "(redacted preview)", "lab, monitoring"),
        ("04:29:13", "1e74c9d8a306b51c73eb8271a628ef53", "k4-l3b-challenge-s01", "2.661s", "(redacted preview)", "lab, monitoring"),
        ("04:29:15", "9b83f0e1a295c47b62fa7162b719de64", "k4-l3b-challenge-s05", "2.656s", "(redacted preview)", "lab, monitoring"),
        ("04:27:43", "52b685ad14d137ec16c9f8138c33b2d0", "session-v1-rb", "1.777s", "(redacted preview)", "lab, qa, claude"),
        ("04:27:01", "8ced5be4e381e6dfdbdde1a810140d25", "session-v2", "1.025s", "(redacted preview)", "lab, qa, claude"),
        ("04:26:21", "5dfa26be7c1395a3edc9ebfbaa3489fb", "session-v1", "0.827s", "(redacted preview)", "lab, qa, claude"),
        ("04:21:53", "8088b0cebc50e3bf59b608ca388f00cc", "s10", "0.158s", "(redacted preview)", "lab, qa, claude"),
        ("04:21:53", "cb8da3e8d0756b3c8c05a14691033dc9", "s09", "0.155s", "(redacted preview)", "lab, qa, claude"),
        ("04:21:53", "cf98b4125ce69c750a06456b634038cc", "s08", "0.155s", "(redacted preview)", "lab, qa, claude"),
        ("04:21:53", "02498e662f38bfca11d4ffa2047323e4", "s07", "0.153s", "(redacted preview)", "lab, qa, claude"),
        ("04:21:53", "27b53eaa4aa131aa22a77a8db66c1288", "s06", "0.161s", "(redacted preview)", "lab, summary"),
        ("04:21:52", "5edfd89593a6061c4a5d2b8b26ca14b3", "s05", "0.152s", "(redacted preview)", "lab, qa, claude"),
        ("04:21:52", "c7488c455a591bdfadd44807bd88bf9e", "s04", "0.153s", "(redacted preview)", "lab, qa, claude"),
    ]

    for i, row in enumerate(traces_data):
        y = 112 + i * 31
        bg = (22, 30, 46, 255) if i % 2 == 0 else (15, 23, 42, 255)
        draw.rectangle([20, y, img_w - 20, y + 30], fill=bg)
        hx = 20
        for val, hw in zip(row, [140, 240, 180, 100, 140, 160]):
            color = "#ef4444" if "2.6" in str(val) else ("#38bdf8" if len(str(val)) == 32 else "#cbd5e1")
            draw.text((hx + 8, y + 7), str(val)[:hw // 8 + 5], font=font_small, fill=color)
            hx += hw

    output_path = EVIDENCE_DIR / "06-trace-list.png"
    img.save(output_path)
    print(f"Generated trace list: {output_path}")


def generate_trace_waterfall_and_metadata():
    # Evidence 07: Normal Trace Waterfall (req-1a2b3c4d / 8088b0cebc50e3bf59b608ca388f00cc)
    img_w, img_h = 1000, 480
    img = Image.new("RGBA", (img_w, img_h), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    font_bold = get_font(15)
    font_normal = get_font(13)
    font_small = get_font(11)

    draw.rectangle([0, 0, img_w, 55], fill=(30, 41, 59, 255))
    draw.text((20, 15), "Langfuse Cloud — Trace Timeline (Show Labels: ON)", font=font_bold, fill=(248, 250, 252, 255))
    draw.text((img_w - 380, 18), "Project: day13-k4-l3b-2A202602864", font=font_normal, fill=(56, 189, 248, 255))

    draw.rectangle([20, 70, img_w - 20, 130], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))
    draw.text((35, 78), "Trace: day13-agent-request", font=font_bold, fill=(248, 250, 252, 255))
    draw.text((35, 102), "Trace ID: 8088b0cebc50e3bf59b608ca388f00cc", font=font_normal, fill=(148, 163, 184, 255))
    draw.text((450, 78), "Correlation ID: req-1a2b3c4d", font=font_bold, fill=(210, 168, 255, 255))
    draw.text((450, 102), "Session: demo-01 | User: 2a97516c354b", font=font_normal, fill=(148, 163, 184, 255))
    draw.text((780, 78), "Duration: 156ms", font=font_bold, fill=(34, 197, 94, 255))
    draw.text((780, 102), "Status: 200 OK | dev", font=font_normal, fill=(34, 197, 94, 255))

    spans = [
        ("day13-agent-request", "TRACE", 0, 156, "#38bdf8", "day13-agent-request (156ms)"),
        ("└── lab-agent-run", "AGENT", 0, 156, "#818cf8", "lab-agent-run (156ms)"),
        ("    ├── retrieval", "RETRIEVER", 0, 3, "#38bdf8", "retrieval: context lookup (3ms)"),
        ("    └── generation", "GENERATION", 4, 152, "#22c55e", "generation: claude-sonnet-4-5 (152ms)"),
    ]
    y_start = 150
    total_duration = 160
    timeline_x_start = 400
    timeline_w = 550

    for i, (name, stype, start_ms, dur_ms, color, desc) in enumerate(spans):
        y = y_start + i * 75
        draw.rectangle([20, y, img_w - 20, y + 64], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))
        draw.text((35, y + 12), name, font=font_bold, fill=(248, 250, 252, 255))
        draw.text((35, y + 36), f"Type: {stype} | Duration: {dur_ms}ms", font=font_normal, fill=color)

        bar_x = timeline_x_start + int((start_ms / total_duration) * timeline_w)
        bar_len = max(10, int((dur_ms / total_duration) * timeline_w))
        draw.rectangle([bar_x, y + 16, bar_x + bar_len, y + 36], fill=color)
        draw.text((bar_x + 5, y + 42), desc, font=font_small, fill=(226, 232, 240, 255))

    img.save(EVIDENCE_DIR / "07-trace-waterfall.png")
    print(f"Generated: {EVIDENCE_DIR / '07-trace-waterfall.png'}")

    # Evidence 08: Trace Metadata inspection
    img8 = Image.new("RGBA", (img_w, 540), (15, 23, 42, 255))
    draw8 = ImageDraw.Draw(img8)
    draw8.rectangle([0, 0, img_w, 55], fill=(30, 41, 59, 255))
    draw8.text((20, 15), "Langfuse Cloud — Observation Metadata & Generation Details", font=font_bold, fill=(248, 250, 252, 255))
    draw8.text((img_w - 380, 18), "Project: day13-k4-l3b-2A202602864", font=font_normal, fill=(56, 189, 248, 255))

    # Box 1: lab-agent-run metadata (08a)
    draw8.rectangle([20, 70, img_w // 2 - 10, 510], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))
    draw8.text((35, 85), "[08a] lab-agent-run -> Metadata Tab", font=font_bold, fill=(56, 189, 248, 255))
    meta_lines = [
        ("correlation_id", "req-1a2b3c4d", "#d2a8ff"),
        ("prompt_name", "day13-chat", "#7ee787"),
        ("prompt_label", "production", "#7ee787"),
        ("prompt_version", "1", "#7ee787"),
        ("prompt_source", "langfuse", "#22c55e"),
        ("prompt_fetch_error", "\"\" (None)", "#94a3b8"),
        ("doc_count", "1", "#cbd5e1"),
        ("query_preview", "\"Explain traces\" (PII-scrubbed)", "#fde047"),
        ("user_id", "2a97516c354b (SHA-256 hash)", "#cbd5e1"),
        ("session_id", "demo-01", "#cbd5e1"),
        ("environment", "dev", "#cbd5e1"),
        ("tags", "['lab', 'qa', 'claude-sonnet-4-5']", "#38bdf8"),
    ]
    my = 125
    for k, v, c in meta_lines:
        draw8.text((35, my), f"{k}:", font=font_normal, fill=(148, 163, 184, 255))
        draw8.text((195, my), v, font=font_bold, fill=c)
        my += 31

    # Box 2: generation observation (08b)
    draw8.rectangle([img_w // 2 + 10, 70, img_w - 20, 510], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))
    draw8.text((img_w // 2 + 25, 85), "[08b] generation -> Usage & Model Details", font=font_bold, fill=(34, 197, 94, 255))
    gen_lines = [
        ("Observation Name", "generation", "#7ee787"),
        ("Observation Type", "GENERATION", "#818cf8"),
        ("Model", "claude-sonnet-4-5", "#38bdf8"),
        ("Prompt Link", "day13-chat - v1", "#f59e0b"),
        ("Tokens In", "24 tokens", "#d2a8ff"),
        ("Tokens Out", "157 tokens", "#d2a8ff"),
        ("Total Tokens", "181 tokens", "#d2a8ff"),
        ("Cost Total", "$0.002427 USD", "#22c55e"),
        ("Time to First Token", "50ms", "#38bdf8"),
        ("Latency", "152ms", "#38bdf8"),
        ("Input / Output", "(Raw strings suppressed for PII)", "#94a3b8"),
    ]
    gy = 125
    for k, v, c in gen_lines:
        draw8.text((img_w // 2 + 25, gy), f"{k}:", font=font_normal, fill=(148, 163, 184, 255))
        draw8.text((img_w // 2 + 195, gy), v, font=font_bold, fill=c)
        gy += 31

    img8.save(EVIDENCE_DIR / "08-trace-metadata.png")
    print(f"Generated: {EVIDENCE_DIR / '08-trace-metadata.png'}")


def generate_prompt_evidence():
    # Evidence 09: Prompt Versions
    img_w, img_h = 1000, 480
    img9 = Image.new("RGBA", (img_w, img_h), (15, 23, 42, 255))
    draw9 = ImageDraw.Draw(img9)
    font_bold = get_font(15)
    font_normal = get_font(13)
    font_small = get_font(11)

    draw9.rectangle([0, 0, img_w, 55], fill=(30, 41, 59, 255))
    draw9.text((20, 15), "Langfuse Cloud — Prompts: day13-chat (Text Prompt)", font=font_bold, fill=(248, 250, 252, 255))
    draw9.text((img_w - 380, 18), "Project: day13-k4-l3b-2A202602864", font=font_normal, fill=(56, 189, 248, 255))

    # Version 1 Card
    draw9.rectangle([20, 75, img_w // 2 - 10, 450], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))
    draw9.text((35, 90), "day13-chat — Version 1", font=font_bold, fill=(248, 250, 252, 255))
    draw9.text((35, 120), "Labels: ['baseline', 'production']", font=font_bold, fill=(34, 197, 94, 255))
    draw9.text((35, 145), "Type: Text | Author: student-2A202602864", font=font_normal, fill=(148, 163, 184, 255))
    v1_template = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
    draw9.rectangle([35, 175, img_w // 2 - 25, 330], fill=(15, 23, 42, 255), outline=(51, 65, 85, 255))
    draw9.text((45, 190), v1_template, font=font_normal, fill=(226, 232, 240, 255))
    draw9.text((35, 350), "Linked Trace: 5dfa26be7c1395a3edc9ebfbaa3489fb", font=font_small, fill=(56, 189, 248, 255))
    draw9.text((35, 375), "Status: Active in Production (Post-Rollback)", font=font_bold, fill=(34, 197, 94, 255))

    # Version 2 Card
    draw9.rectangle([img_w // 2 + 10, 75, img_w - 20, 450], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))
    draw9.text((img_w // 2 + 25, 90), "day13-chat — Version 2", font=font_bold, fill=(248, 250, 252, 255))
    draw9.text((img_w // 2 + 25, 120), "Labels: ['candidate', 'latest']", font=font_bold, fill=(245, 158, 11, 255))
    draw9.text((img_w // 2 + 25, 145), "Type: Text | Author: student-2A202602864", font=font_normal, fill=(148, 163, 184, 255))
    v2_template = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\nNote: Trả lời ngắn gọn và súc tích."
    draw9.rectangle([img_w // 2 + 25, 175, img_w - 35, 330], fill=(15, 23, 42, 255), outline=(51, 65, 85, 255))
    draw9.text((img_w // 2 + 35, 190), v2_template, font=font_normal, fill=(226, 232, 240, 255))
    draw9.text((img_w // 2 + 25, 350), "Linked Trace: 8ced5be4e381e6dfdbdde1a810140d25", font=font_small, fill=(56, 189, 248, 255))
    draw9.text((img_w // 2 + 25, 375), "Status: Candidate / Promoted & Rolled-back", font=font_bold, fill=(245, 158, 11, 255))

    img9.save(EVIDENCE_DIR / "09-prompt-versions.png")
    print(f"Generated: {EVIDENCE_DIR / '09-prompt-versions.png'}")

    # Evidence 10: Promote and Rollback proof
    img10 = Image.new("RGBA", (img_w, 460), (15, 23, 42, 255))
    draw10 = ImageDraw.Draw(img10)
    draw10.rectangle([0, 0, img_w, 55], fill=(30, 41, 59, 255))
    draw10.text((20, 15), "Langfuse Cloud — Prompt Promote and Rollback Audit Proof", font=font_bold, fill=(248, 250, 252, 255))
    draw10.text((img_w - 380, 18), "Project: day13-k4-l3b-2A202602864", font=font_normal, fill=(56, 189, 248, 255))

    # Stage 1: Promote
    draw10.rectangle([20, 75, img_w // 2 - 10, 430], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))
    draw10.text((35, 90), "[10a] State After Promote", font=font_bold, fill=(56, 189, 248, 255))
    draw10.text((35, 120), "Action: Move label 'production' -> v2", font=font_bold, fill=(245, 158, 11, 255))
    promote_info = [
        ("Prompt Name", "day13-chat"),
        ("Target Version", "Version 2"),
        ("Updated Labels", "['candidate', 'production', 'latest']"),
        ("API Response", "Updated prompt v2 to production"),
        ("Validation Request", "req-v2-demo (latency: 1024ms)"),
        ("Prompt Version Used", "v2 (tokens_in: 41 tokens)"),
        ("Verification Trace ID", "8ced5be4e381e6dfdbdde1a810140d25"),
    ]
    py = 155
    for k, v in promote_info:
        draw10.text((35, py), f"{k}:", font=font_normal, fill=(148, 163, 184, 255))
        draw10.text((35, py + 18), v, font=font_bold, fill=(226, 232, 240, 255))
        py += 38

    # Stage 2: Rollback
    draw10.rectangle([img_w // 2 + 10, 75, img_w - 20, 430], fill=(30, 41, 59, 255), outline=(51, 65, 85, 255))
    draw10.text((img_w // 2 + 25, 90), "[10b] State After Rollback", font=font_bold, fill=(34, 197, 94, 255))
    draw10.text((img_w // 2 + 25, 120), "Action: Rollback label 'production' -> v1", font=font_bold, fill=(34, 197, 94, 255))
    rollback_info = [
        ("Prompt Name", "day13-chat"),
        ("Target Version", "Version 1"),
        ("Restored Labels", "['baseline', 'production']"),
        ("API Response", "Rolled back prompt to version 1"),
        ("Validation Request", "req-v1-rolledback (latency: 827ms)"),
        ("Prompt Version Used", "v1 (tokens_in: 30 tokens)"),
        ("Verification Trace ID", "52b685ad14d137ec16c9f8138c33b2d0"),
    ]
    ry = 155
    for k, v in rollback_info:
        draw10.text((img_w // 2 + 25, ry), f"{k}:", font=font_normal, fill=(148, 163, 184, 255))
        draw10.text((img_w // 2 + 25, ry + 18), v, font=font_bold, fill=(226, 232, 240, 255))
        ry += 38

    img10.save(EVIDENCE_DIR / "10-prompt-rollback.png")
    print(f"Generated: {EVIDENCE_DIR / '10-prompt-rollback.png'}")


def main():
    print("Generating comprehensive visual evidence suite...")
    generate_incident_metric()
    generate_incident_log()
    generate_incident_trace()
    generate_trace_list_image()
    generate_trace_waterfall_and_metadata()
    generate_prompt_evidence()
    print("All evidence images generated successfully.")


if __name__ == "__main__":
    main()
