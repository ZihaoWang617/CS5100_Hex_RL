"""
Batch evaluation helpers for Hex players.
"""

import argparse
import os
import sys
from typing import Callable, Dict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.constants import Color
from engine.game import GameController
from players.q_learning_player import ApproximateQLearningPlayer
from players.random_player import RandomPlayer


PlayerFactory = Callable[[Color], object]


def play_single_game(red_factory: PlayerFactory, blue_factory: PlayerFactory, board_size: int) -> Dict[str, object]:
    game = GameController(board_size=board_size)
    red_player = red_factory(Color.RED)
    blue_player = blue_factory(Color.BLUE)

    if not game.start_game(red_player, blue_player):
        raise RuntimeError("Failed to initialize players.")

    while game.play_turn():
        pass

    red_player.cleanup()
    blue_player.cleanup()

    return game.get_game_summary()


def run_match_series(red_factory: PlayerFactory, blue_factory: PlayerFactory, board_size: int, games: int) -> Dict[str, float]:
    red_wins = 0
    blue_wins = 0
    draws = 0
    total_turns = 0

    for _ in range(games):
        summary = play_single_game(red_factory, blue_factory, board_size)
        total_turns += summary["total_turns"]

        if summary["winner"] == Color.RED.name:
            red_wins += 1
        elif summary["winner"] == Color.BLUE.name:
            blue_wins += 1
        else:
            draws += 1

    return {
        "games": games,
        "red_win_rate": red_wins / float(games),
        "blue_win_rate": blue_wins / float(games),
        "draw_rate": draws / float(games),
        "average_turns": total_turns / float(games),
    }


def build_player_factory(player_kind: str, weights_path: str = "") -> PlayerFactory:
    if player_kind == "random":
        return lambda color: RandomPlayer(color)
    if player_kind == "q":
        def factory(color: Color):
            player = ApproximateQLearningPlayer(color, epsilon=0.0)
            if weights_path:
                player.load_weights(weights_path)
            return player
        return factory
    raise ValueError(f"Unsupported player kind: {player_kind}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repeated Hex matches between two player types.")
    parser.add_argument("--red", choices=["random", "q"], default="random")
    parser.add_argument("--blue", choices=["random", "q"], default="random")
    parser.add_argument("--red-weights", default="")
    parser.add_argument("--blue-weights", default="")
    parser.add_argument("--board-size", type=int, default=7)
    parser.add_argument("--games", type=int, default=50)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    summary = run_match_series(
        build_player_factory(args.red, args.red_weights),
        build_player_factory(args.blue, args.blue_weights),
        board_size=args.board_size,
        games=args.games,
    )
    for key, value in summary.items():
        print(f"{key}: {value}")
