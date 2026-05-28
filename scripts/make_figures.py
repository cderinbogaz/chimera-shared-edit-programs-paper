#!/usr/bin/env python3
"""Generate publication figures for the Chimera shared edit-program paper."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "paper" / "figures"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def workload_name(raw: str) -> str:
    if "shared_edit_program" in raw:
        return "Chimera"
    if "unified_diff" in raw:
        return "Unified diff"
    return raw


def profile_name(raw: str) -> str:
    return {
        "normal": "vLLM",
        "mtp": "MTP-2",
        "mtp_depth6": "MTP-6",
    }.get(raw, raw)


def num(row: dict[str, str], key: str) -> float:
    return float(row[key])


def style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "axes.edgecolor": "#1f2933",
            "axes.labelcolor": "#111827",
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": "#111827",
            "ytick.color": "#111827",
            "grid.color": "#d9dee7",
            "grid.linewidth": 0.8,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.03,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=300)
    plt.close(fig)


def comma(x: float, _pos: object) -> str:
    return f"{x:,.0f}"


def figure_artifact_throughput(rows: list[dict[str, str]]) -> None:
    order = ["normal", "mtp", "mtp_depth6"]
    by_key = {(r["profile"], workload_name(r["workload"])): r for r in rows}
    x = list(range(len(order)))
    width = 0.34
    colors = {"Unified diff": "#4C78A8", "Chimera": "#F58518"}

    fig, ax = plt.subplots(figsize=(6.4, 3.45))
    for offset, workload in [(-width / 2, "Unified diff"), (width / 2, "Chimera")]:
        vals = [num(by_key[(profile, workload)], "artifact_tokens_per_s") for profile in order]
        bars = ax.bar(
            [i + offset for i in x],
            vals,
            width,
            label=workload,
            color=colors[workload],
            edgecolor="#111827",
            linewidth=0.7,
        )
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val + 130,
                f"{val/1000:.1f}k",
                ha="center",
                va="bottom",
                fontsize=8.5,
            )

    ax.set_title("Artifact throughput on 50 long-context code-edit episodes")
    ax.set_ylabel("Validated artifact tokens / second")
    ax.set_xticks(x, [profile_name(p) for p in order])
    ax.yaxis.set_major_formatter(FuncFormatter(comma))
    ax.set_ylim(0, 8500)
    ax.grid(axis="y")
    ax.legend(ncol=2, loc="upper right")
    ax.text(
        0.01,
        -0.23,
        "Qwen3.6-35B-A3B-FP8, vLLM 0.21.0, 1x H100, 100K-context LongCodeBench-derived edits.",
        transform=ax.transAxes,
        fontsize=8,
        color="#4b5563",
    )
    save(fig, "artifact_throughput")


def figure_speedup_ci(rows: list[dict[str, str]]) -> None:
    wanted = [
        ("normal unified diff", "normal shared edit program", "vLLM: Chimera vs diff"),
        ("MTP unified diff", "MTP shared edit program", "MTP-2: Chimera vs diff"),
        ("normal unified diff", "MTP shared edit program", "MTP-2 + Chimera vs vLLM diff"),
        (
            "MTP depth 2 shared edit program",
            "MTP depth 6 shared edit program",
            "MTP-6 vs MTP-2, Chimera",
        ),
    ]
    selected = []
    for baseline, treatment, label in wanted:
        for row in rows:
            if (
                row["baseline"] == baseline
                and row["treatment"] == treatment
                and row["metric"] == "artifact_tokens_per_s"
            ):
                selected.append((label, row))
                break

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    y = list(range(len(selected)))[::-1]
    means = [num(row, "mean_speedup") for _label, row in selected]
    lows = [num(row, "ci95_low") for _label, row in selected]
    highs = [num(row, "ci95_high") for _label, row in selected]
    xerr = [[m - lo for m, lo in zip(means, lows)], [hi - m for m, hi in zip(means, highs)]]
    colors = ["#F58518", "#F58518", "#54A24B", "#B279A2"]

    ax.errorbar(
        means,
        y,
        xerr=xerr,
        fmt="o",
        markersize=7,
        elinewidth=2,
        capsize=4,
        color="#111827",
        ecolor="#111827",
    )
    for yi, mean, color in zip(y, means, colors):
        ax.scatter([mean], [yi], s=70, color=color, edgecolor="#111827", linewidth=0.8, zorder=3)
        ax.text(mean + 0.05, yi, f"{mean:.2f}x", va="center", fontsize=9)

    ax.axvline(1.0, color="#6b7280", linestyle="--", linewidth=1.0)
    ax.set_yticks(y, [label for label, _row in selected])
    ax.set_xlabel("Mean paired artifact-throughput speedup (95% bootstrap CI)")
    ax.set_xlim(0.75, 2.15)
    ax.grid(axis="x")
    ax.set_title("Chimera speedup survives a unified-diff baseline")
    save(fig, "paired_speedups")


def figure_latency(rows: list[dict[str, str]]) -> None:
    order = [
        ("normal", "Unified diff"),
        ("normal", "Chimera"),
        ("mtp", "Unified diff"),
        ("mtp", "Chimera"),
        ("mtp_depth6", "Unified diff"),
        ("mtp_depth6", "Chimera"),
    ]
    by_key = {(r["profile"], workload_name(r["workload"])): r for r in rows}
    labels = [f"{profile_name(p)}\n{w}" for p, w in order]
    avg = [num(by_key[key], "episode_latency_avg_s") for key in order]
    p95 = [num(by_key[key], "episode_latency_p95_s") for key in order]
    colors = ["#4C78A8" if w == "Unified diff" else "#F58518" for _p, w in order]

    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    x = range(len(order))
    ax.bar(x, p95, color="#d5dbe7", edgecolor="#111827", linewidth=0.6, label="p95")
    bars = ax.bar(x, avg, color=colors, edgecolor="#111827", linewidth=0.7, label="mean")
    for bar, val in zip(bars, avg):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.08, f"{val:.2f}s", ha="center", fontsize=8)
    ax.set_xticks(list(x), labels, fontsize=8)
    ax.set_ylabel("Episode latency (seconds)")
    ax.set_title("Shared edit programs reduce end-to-end episode latency")
    ax.set_ylim(0, 5.1)
    ax.grid(axis="y")
    ax.legend(loc="upper right")
    save(fig, "latency")


def figure_token_accounting(rows: list[dict[str, str]]) -> None:
    by_key = {(r["profile"], workload_name(r["workload"])): r for r in rows}
    diff = by_key[("normal", "Unified diff")]
    chimera = by_key[("normal", "Chimera")]
    labels = ["Unified diff", "Chimera"]
    output = [num(diff, "model_output_tokens"), num(chimera, "model_output_tokens")]
    artifact = [num(diff, "artifact_tokens"), num(chimera, "artifact_tokens")]

    fig, axes = plt.subplots(1, 2, figsize=(6.7, 3.05))
    axes[0].bar(labels, output, color=["#4C78A8", "#F58518"], edgecolor="#111827", linewidth=0.7)
    axes[0].set_title("Model tokens emitted")
    axes[0].set_ylabel("Tokens")
    axes[0].yaxis.set_major_formatter(FuncFormatter(comma))
    axes[0].grid(axis="y")
    for i, val in enumerate(output):
        axes[0].text(i, val + 250, f"{val:,.0f}", ha="center", fontsize=8.5)

    axes[1].bar(labels, artifact, color=["#4C78A8", "#F58518"], edgecolor="#111827", linewidth=0.7)
    axes[1].set_title("Validated artifact produced")
    axes[1].yaxis.set_major_formatter(FuncFormatter(comma))
    axes[1].grid(axis="y")
    for i, val in enumerate(artifact):
        axes[1].text(i, val + 9000, f"{val:,.0f}", ha="center", fontsize=8.5)

    fig.suptitle("Same rendered artifact, fewer emitted model tokens", fontweight="bold", y=1.03)
    save(fig, "token_accounting")


def main() -> None:
    style()
    summary = read_csv(DATA / "summary.csv")
    speedups = read_csv(DATA / "paired_speedups.csv")
    figure_artifact_throughput(summary)
    figure_speedup_ci(speedups)
    figure_latency(summary)
    figure_token_accounting(summary)
    print(f"wrote figures to {FIG}")


if __name__ == "__main__":
    main()
