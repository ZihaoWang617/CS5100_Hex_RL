"""
Thread 1 experiment: Minimax vs Random across board sizes and search depths.

Measures win rate and average move time for the Minimax player.

Usage:
    python evaluation/run_minimax_experiments.py
    python evaluation/run_minimax_experiments.py --games 20 --output results/minimax_exp.csv
    python evaluation/run_minimax_experiments.py --depths 2 3 --sizes 7 9
"""

import argparse
import csv
import os
import sys
import time
from typing import List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.constants import Color
from engine.game import GameController
from players.minimax_player import MinimaxPlayer
from players.random_player import RandomPlayer


def run_single_game(board_size: int, depth: int) -> dict:
    """Run one game of Minimax (RED) vs Random (BLUE), return per-game stats."""
    minimax = MinimaxPlayer(Color.RED, depth=depth, name=f"Minimax-d{depth}")
    random_p = RandomPlayer(Color.BLUE, name="Random")

    game = GameController(board_size=board_size)
    if not game.start_game(minimax, random_p):
        raise RuntimeError("Failed to start game.")

    move_times: List[float] = []

    while True:
        before = time.time()
        ongoing = game.play_turn()
        elapsed = time.time() - before

        # Only record the minimax player's move time
        if minimax.last_move_time > 0:
            move_times.append(minimax.last_move_time)
            minimax.last_move_time = 0.0

        if not ongoing:
            break

    minimax.cleanup()
    random_p.cleanup()

    summary = game.get_game_summary()
    minimax_won = summary["winner"] == Color.RED.name
    avg_move_time = sum(move_times) / len(move_times) if move_times else 0.0

    return {
        "won": minimax_won,
        "total_turns": summary["total_turns"],
        "avg_move_time": avg_move_time,
        "max_move_time": max(move_times) if move_times else 0.0,
    }


def run_experiment(board_size: int, depth: int, games: int) -> dict:
    wins = 0
    total_turns = 0
    all_avg_times: List[float] = []
    all_max_times: List[float] = []

    for _ in range(games):
        result = run_single_game(board_size, depth)
        if result["won"]:
            wins += 1
        total_turns += result["total_turns"]
        all_avg_times.append(result["avg_move_time"])
        all_max_times.append(result["max_move_time"])

    return {
        "board_size": board_size,
        "depth": depth,
        "games": games,
        "win_rate": wins / games,
        "avg_turns": total_turns / games,
        "avg_move_time_s": sum(all_avg_times) / len(all_avg_times),
        "max_move_time_s": max(all_max_times),
    }


def main():
    parser = argparse.ArgumentParser(description="Minimax experiment runner.")
    parser.add_argument("--games", type=int, default=10, help="Games per (size, depth) config")
    parser.add_argument("--depths", type=int, nargs="+", default=[2, 3, 4, 5])
    parser.add_argument("--sizes", type=int, nargs="+", default=[7, 9, 11, 13])
    parser.add_argument("--output", default="", help="CSV output path (optional)")
    args = parser.parse_args()

    rows = []
    header = ["board_size", "depth", "games", "win_rate", "avg_turns", "avg_move_time_s", "max_move_time_s"]

    print(f"{'size':>6} {'depth':>6} {'games':>6} {'win_rate':>9} {'avg_turns':>10} {'avg_ms':>9} {'max_ms':>9}")
    print("-" * 65)

    for size in args.sizes:
        for depth in args.depths:
            result = run_experiment(size, depth, args.games)
            rows.append(result)
            print(
                f"{size:>6} {depth:>6} {args.games:>6} "
                f"{result['win_rate']:>9.3f} "
                f"{result['avg_turns']:>10.1f} "
                f"{result['avg_move_time_s']*1000:>9.1f} "
                f"{result['max_move_time_s']*1000:>9.1f}"
            )

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
