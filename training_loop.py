"""
Training entry point for the approximate Q-learning Hex player.
"""

import argparse
import csv
import os
from typing import Dict, List

from engine.constants import Color
from players.q_learning_player import ApproximateQLearningPlayer, play_self_play_episode
from players.random_player import RandomPlayer
from evaluation.run_matches import run_match_series


def train_agent(
    board_size: int,
    episodes: int,
    alpha: float,
    gamma: float,
    epsilon: float,
    epsilon_decay: float,
    min_epsilon: float,
    eval_interval: int,
    eval_games: int,
    output_dir: str,
) -> List[Dict[str, float]]:
    os.makedirs(output_dir, exist_ok=True)

    red_agent = ApproximateQLearningPlayer(Color.RED, "Q-Red", alpha=alpha, gamma=gamma, epsilon=epsilon)
    blue_agent = ApproximateQLearningPlayer(Color.BLUE, "Q-Blue", alpha=alpha, gamma=gamma, epsilon=epsilon)
    red_agent.initialize(board_size)
    blue_agent.initialize(board_size)

    history: List[Dict[str, float]] = []

    for episode in range(1, episodes + 1):
        winner = play_self_play_episode(red_agent, blue_agent, board_size)
        red_agent.epsilon = max(min_epsilon, red_agent.epsilon * epsilon_decay)
        blue_agent.epsilon = red_agent.epsilon

        if episode % eval_interval == 0 or episode == 1 or episode == episodes:
            eval_agent = red_agent.clone_for_evaluation(Color.RED)
            random_agent = RandomPlayer(Color.BLUE, "Random Baseline", seed=episode)
            summary = run_match_series(
                lambda color: eval_agent.clone_for_evaluation(color),
                lambda color: RandomPlayer(color, "Random Baseline", seed=episode + color.value),
                board_size=board_size,
                games=eval_games,
            )
            row = {
                "episode": episode,
                "epsilon": red_agent.epsilon,
                "self_play_winner": winner.name,
                "eval_red_win_rate": summary["red_win_rate"],
                "eval_blue_win_rate": summary["blue_win_rate"],
                "eval_draw_rate": summary["draw_rate"],
                "avg_turns": summary["average_turns"],
            }
            history.append(row)
            red_agent.save_weights(os.path.join(output_dir, f"weights_ep_{episode}.json"))

    csv_path = os.path.join(output_dir, "training_metrics.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)

    return history


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train an approximate Q-learning Hex player.")
    parser.add_argument("--board-size", type=int, default=7)
    parser.add_argument("--episodes", type=int, default=2000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--epsilon", type=float, default=0.20)
    parser.add_argument("--epsilon-decay", type=float, default=0.999)
    parser.add_argument("--min-epsilon", type=float, default=0.02)
    parser.add_argument("--eval-interval", type=int, default=100)
    parser.add_argument("--eval-games", type=int, default=40)
    parser.add_argument("--output-dir", default="artifacts/training")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train_agent(
        board_size=args.board_size,
        episodes=args.episodes,
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon=args.epsilon,
        epsilon_decay=args.epsilon_decay,
        min_epsilon=args.min_epsilon,
        eval_interval=args.eval_interval,
        eval_games=args.eval_games,
        output_dir=args.output_dir,
    )
