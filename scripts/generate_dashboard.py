from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

LOG_PATH = Path("data/logs.jsonl")
OUTPUT_DIR = Path("submission/evidence")


def parse_iso(ts_str: str) -> datetime:
    ts_str = ts_str.replace("Z", "+00:00")
    return datetime.fromisoformat(ts_str)


def generate_dashboard() -> None:
    if not LOG_PATH.exists():
        print(f"Error: {LOG_PATH} does not exist.")
        return

    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except Exception:
                continue

    if not records:
        print("No records found in log file.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter and extract metrics
    req_received = [r for r in records if r.get("event") == "request_received"]
    resp_sent = [r for r in records if r.get("event") == "response_sent"]
    req_failed = [r for r in records if r.get("event") == "request_failed"]

    # Timestamps
    times_sent = [parse_iso(r["ts"]) for r in resp_sent] if resp_sent else [datetime.now(timezone.utc)]
    times_all = [parse_iso(r["ts"]) for r in records if "ts" in r]

    latencies = [r.get("latency_ms", 0) for r in resp_sent] or [0]
    ttfts = [r.get("ttft_ms", 0) for r in resp_sent] or [0]
    tokens_in = [r.get("tokens_in", 0) for r in resp_sent] or [0]
    tokens_out = [r.get("tokens_out", 0) for r in resp_sent] or [0]
    costs = [r.get("cost_usd", 0.0) for r in resp_sent] or [0.0]
    qualities = [r.get("quality_score", 0.0) for r in resp_sent] or [0.0]

    # Tool success rate calculation:
    tool_events = [r for r in records if r.get("tool_success") is not None]
    tool_successes = [r for r in tool_events if r.get("tool_success") is True]
    tool_success_rate = (len(tool_successes) / len(tool_events) * 100) if tool_events else 100.0

    total_requests = len(req_received)
    failed_requests = len(req_failed)
    error_rate = (failed_requests / total_requests * 100) if total_requests else 0.0

    # Percentiles
    p50_lat = np.percentile(latencies, 50) if latencies else 0
    p95_lat = np.percentile(latencies, 95) if latencies else 0
    p99_lat = np.percentile(latencies, 99) if latencies else 0
    ttft_p95 = np.percentile(ttfts, 95) if ttfts else 0

    # Styling configuration
    plt.style.use("seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "default")
    fig, axes = plt.subplots(3, 2, figsize=(15, 12), dpi=150)
    fig.patch.set_facecolor("#0f172a")

    for row in axes:
        for ax in row:
            ax.set_facecolor("#1e293b")
            ax.tick_params(colors="#cbd5e1", labelsize=9)
            ax.xaxis.label.set_color("#94a3b8")
            ax.yaxis.label.set_color("#94a3b8")
            for spine in ax.spines.values():
                spine.set_color("#334155")

    title_text = (
        "K4-L3B Day 13 Monitoring & LLMOps Dashboard\n"
        "Time Range: 60m | Refresh: 30s | Student: Le Minh Sang (2A202602864) | Service: day13-l3b-monitoring-llmops-lab"
    )
    fig.suptitle(title_text, color="#f8fafc", fontsize=15, fontweight="bold", y=0.98)

    indices = list(range(1, len(resp_sent) + 1))

    # 1. Latency Panel
    ax1 = axes[0, 0]
    ax1.plot(indices, latencies, color="#38bdf8", marker="o", markersize=4, label=f"Latency (P50: {p50_lat:.1f}ms, P95: {p95_lat:.1f}ms)")
    ax1.plot(indices, ttfts, color="#a78bfa", linestyle="--", marker="s", markersize=3, label=f"TTFT (P95: {ttft_p95:.1f}ms)")
    ax1.axhline(3000, color="#ef4444", linestyle=":", linewidth=2, label="Threshold P95 <= 3000ms")
    ax1.set_title("1. Latency percentiles and TTFT", color="#f8fafc", fontsize=11, fontweight="bold", pad=8)
    ax1.set_xlabel("Request sequence", fontsize=9)
    ax1.set_ylabel("Latency / TTFT (ms)", fontsize=9)
    ax1.legend(loc="upper right", fontsize=8, facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0")
    ax1.set_ylim(bottom=0, top=max(3500, max(latencies) * 1.2 if latencies else 3500))

    # 2. Traffic Panel
    ax2 = axes[0, 1]
    # Request count by minute
    req_minutes = [t.strftime("%H:%M") for t in times_all]
    unique_mins, counts = np.unique(req_minutes, return_counts=True) if req_minutes else (["00:00"], [0])
    ax2.bar(unique_mins, counts, color="#0ea5e9", width=0.4, label=f"Total: {total_requests} reqs")
    ax2.axhline(1, color="#22c55e", linestyle=":", linewidth=2, label="Threshold >= 1 req/min")
    ax2.set_title("2. Request traffic", color="#f8fafc", fontsize=11, fontweight="bold", pad=8)
    ax2.set_xlabel("Time (HH:MM UTC)", fontsize=9)
    ax2.set_ylabel("Traffic (requests_per_minute)", fontsize=9)
    ax2.legend(loc="upper right", fontsize=8, facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0")
    ax2.set_ylim(bottom=0, top=max(5, max(counts) * 1.3 if len(counts) else 5))

    # 3. Errors Panel
    ax3 = axes[1, 0]
    categories = ["Error Rate (%)", "Retrieval Success (%)"]
    values = [error_rate, tool_success_rate]
    bar_colors = ["#ef4444" if error_rate > 2 else "#22c55e", "#22c55e" if tool_success_rate >= 90 else "#ef4444"]
    bars = ax3.bar(categories, values, color=bar_colors, width=0.45)
    for bar, val in zip(bars, values):
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"{val:.1f}%", ha="center", color="#f8fafc", fontweight="bold", fontsize=9)
    ax3.axhline(2, color="#ef4444", linestyle=":", linewidth=1.5, label="Max Error Rate Threshold (2%)")
    ax3.axhline(90, color="#38bdf8", linestyle="--", linewidth=1.5, label="Min Retrieval Success Threshold (90%)")
    ax3.set_title("3. Error rate and retrieval success", color="#f8fafc", fontsize=11, fontweight="bold", pad=8)
    ax3.set_ylabel("Percent (%)", fontsize=9)
    ax3.set_ylim(0, 115)
    ax3.legend(loc="upper right", fontsize=8, facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0")

    # 4. Cost Panel
    ax4 = axes[1, 1]
    cum_costs = np.cumsum(costs)
    ax4.plot(indices, cum_costs, color="#10b981", marker="o", markersize=4, label=f"Cumulative Cost: ${cum_costs[-1]:.4f}")
    ax4.axhline(2.5, color="#f59e0b", linestyle=":", linewidth=2, label="Daily Budget Threshold <= $2.50")
    ax4.set_title("4. Cost over time", color="#f8fafc", fontsize=11, fontweight="bold", pad=8)
    ax4.set_xlabel("Request sequence", fontsize=9)
    ax4.set_ylabel("Cost (usd)", fontsize=9)
    ax4.legend(loc="upper left", fontsize=8, facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0")
    ax4.set_ylim(0, 3.0)

    # 5. Tokens Panel
    ax5 = axes[2, 0]
    total_tokens_in = sum(tokens_in)
    total_tokens_out = sum(tokens_out)
    total_tokens = total_tokens_in + total_tokens_out
    ax5.bar(["Tokens In", "Tokens Out"], [total_tokens_in, total_tokens_out], color=["#6366f1", "#ec4899"], width=0.45)
    ax5.text(0, total_tokens_in + 20, str(total_tokens_in), ha="center", color="#f8fafc", fontweight="bold")
    ax5.text(1, total_tokens_out + 20, str(total_tokens_out), ha="center", color="#f8fafc", fontweight="bold")
    ax5.axhline(50000, color="#f43f5e", linestyle=":", linewidth=2, label="Threshold <= 50,000 tokens")
    ax5.set_title(f"5. Input and output tokens (Total: {total_tokens})", color="#f8fafc", fontsize=11, fontweight="bold", pad=8)
    ax5.set_ylabel("Tokens", fontsize=9)
    ax5.legend(loc="upper right", fontsize=8, facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0")
    ax5.set_ylim(0, max(60000, max(total_tokens_in, total_tokens_out) * 1.3))

    # 6. Quality Panel
    ax6 = axes[2, 1]
    mean_quality = np.mean(qualities) if qualities else 0.0
    ax6.plot(indices, qualities, color="#f59e0b", marker="d", markersize=4, label=f"Quality Score (Mean: {mean_quality:.2f})")
    ax6.axhline(0.75, color="#ef4444", linestyle=":", linewidth=2, label="Min Quality Threshold >= 0.75")
    ax6.set_title("6. Quality proxy", color="#f8fafc", fontsize=11, fontweight="bold", pad=8)
    ax6.set_xlabel("Request sequence", fontsize=9)
    ax6.set_ylabel("Quality Score (score_0_to_1)", fontsize=9)
    ax6.legend(loc="lower right", fontsize=8, facecolor="#1e293b", edgecolor="#475569", labelcolor="#e2e8f0")
    ax6.set_ylim(0.0, 1.1)

    plt.tight_layout(rect=[0, 0.03, 1, 0.94])
    output_path = OUTPUT_DIR / "11-dashboard-overview.png"
    plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Dashboard successfully generated and saved to: {output_path}")


if __name__ == "__main__":
    generate_dashboard()
