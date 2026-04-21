"""
Visualize Minimax experiment results from one or more CSV files.

Usage:
    python evaluation/plot_minimax_results.py --input results/minimax_results.csv
    python evaluation/plot_minimax_results.py --input results/minimax_results.csv results/minimax_depth5.csv --output results/
"""

import argparse
import csv
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
except ImportError:
    print("matplotlib not installed. Run: pip install matplotlib")
    sys.exit(1)


MARKERS = ["o", "s", "^", "D"]
COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63"]


def load_csv(path: str) -> list:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def group_by_size(rows: list) -> dict:
    groups = {}
    for row in rows:
        size = int(row["board_size"])
        groups.setdefault(size, []).append(row)
    return dict(sorted(groups.items()))


def plot_win_rate(groups: dict, output_dir: str):
    fig, ax = plt.subplots(figsize=(7, 5))

    for i, (size, rows) in enumerate(groups.items()):
        rows_sorted = sorted(rows, key=lambda r: int(r["depth"]))
        depths = [int(r["depth"]) for r in rows_sorted]
        win_rates = [float(r["win_rate"]) * 100 for r in rows_sorted]
        ax.plot(depths, win_rates, marker=MARKERS[i % len(MARKERS)],
                color=COLORS[i % len(COLORS)], label=f"{size}×{size}", linewidth=2)

    ax.set_xlabel("Search Depth", fontsize=12)
    ax.set_ylabel("Win Rate (%)", fontsize=12)
    ax.set_title("Minimax Win Rate vs Random by Board Size", fontsize=13, fontweight="bold")
    ax.set_ylim(-5, 105)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f%%"))
    ax.set_xticks(sorted({int(r["depth"]) for rows in groups.values() for r in rows}))
    ax.legend(title="Board Size", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()

    path = os.path.join(output_dir, "minimax_win_rate.png")
    fig.savefig(path, dpi=150)
    print(f"Saved: {path}")
    plt.close(fig)


def plot_move_time(groups: dict, output_dir: str):
    fig, ax = plt.subplots(figsize=(7, 5))

    for i, (size, rows) in enumerate(groups.items()):
        rows_sorted = sorted(rows, key=lambda r: int(r["depth"]))
        depths = [int(r["depth"]) for r in rows_sorted]
        avg_ms = [float(r["avg_move_time_s"]) * 1000 for r in rows_sorted]
        ax.plot(depths, avg_ms, marker=MARKERS[i % len(MARKERS)],
                color=COLORS[i % len(COLORS)], label=f"{size}×{size}", linewidth=2)

    ax.set_xlabel("Search Depth", fontsize=12)
    ax.set_ylabel("Avg Move Time (ms)", fontsize=12)
    ax.set_title("Minimax Avg Move Time by Board Size", fontsize=13, fontweight="bold")
    ax.set_xticks(sorted({int(r["depth"]) for rows in groups.values() for r in rows}))
    ax.legend(title="Board Size", fontsize=10)
    ax.set_yscale("log")
    ax.grid(True, linestyle="--", alpha=0.5, which="both")
    fig.tight_layout()

    path = os.path.join(output_dir, "minimax_move_time.png")
    fig.savefig(path, dpi=150)
    print(f"Saved: {path}")
    plt.close(fig)


def plot_combined(groups: dict, output_dir: str):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    for i, (size, rows) in enumerate(groups.items()):
        rows_sorted = sorted(rows, key=lambda r: int(r["depth"]))
        depths = [int(r["depth"]) for r in rows_sorted]
        win_rates = [float(r["win_rate"]) * 100 for r in rows_sorted]
        avg_ms = [float(r["avg_move_time_s"]) * 1000 for r in rows_sorted]

        kw = dict(marker=MARKERS[i % len(MARKERS)], color=COLORS[i % len(COLORS)],
                  label=f"{size}×{size}", linewidth=2)
        axes[0].plot(depths, win_rates, **kw)
        axes[1].plot(depths, avg_ms, **kw)

    depth_ticks = sorted({int(r["depth"]) for rows in groups.values() for r in rows})

    axes[0].set_xlabel("Search Depth", fontsize=11)
    axes[0].set_ylabel("Win Rate (%)", fontsize=11)
    axes[0].set_title("Win Rate vs Random", fontsize=12, fontweight="bold")
    axes[0].set_ylim(-5, 105)
    axes[0].yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f%%"))
    axes[0].set_xticks(depth_ticks)
    axes[0].legend(title="Board Size", fontsize=9)
    axes[0].grid(True, linestyle="--", alpha=0.5)

    axes[1].set_xlabel("Search Depth", fontsize=11)
    axes[1].set_ylabel("Avg Move Time (ms)", fontsize=11)
    axes[1].set_title("Avg Move Time (log scale)", fontsize=12, fontweight="bold")
    axes[1].set_xticks(depth_ticks)
    axes[1].set_yscale("log")
    axes[1].legend(title="Board Size", fontsize=9)
    axes[1].grid(True, linestyle="--", alpha=0.5, which="both")

    fig.suptitle("Minimax Alpha-Beta: Performance vs Search Depth", fontsize=14, fontweight="bold")
    fig.tight_layout()

    path = os.path.join(output_dir, "minimax_combined.png")
    fig.savefig(path, dpi=150)
    print(f"Saved: {path}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot Minimax experiment results.")
    parser.add_argument("--input", required=True, help="Path to CSV from run_minimax_experiments.py")
    parser.add_argument("--output", default="", help="Output directory for PNG files (default: same as input)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"File not found: {args.input}")
        sys.exit(1)

    output_dir = args.output or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(output_dir, exist_ok=True)

    rows = load_csv(args.input)
    groups = group_by_size(rows)

    plot_win_rate(groups, output_dir)
    plot_move_time(groups, output_dir)
    plot_combined(groups, output_dir)

    print("Done.")


if __name__ == "__main__":
    main()
