"""
Approximate Q-learning player for Hex.
"""

import json
import math
import random
from collections import deque
from typing import Dict, Iterable, List, Optional, Tuple, Union

from engine.board import HexBoard
from engine.constants import Color
from players.base import Player

Move = Tuple[int, int]
FeatureVector = Dict[str, float]


class ApproximateQLearningPlayer(Player):
    """
    Linear approximate Q-learning agent.

    This first version intentionally uses a compact, interpretable feature set so the
    agent is easy to debug and easy to explain in the final project report.
    """

    def __init__(
        self,
        color: Color,
        name: str = "Approx Q Player",
        alpha: float = 0.05,
        gamma: float = 0.95,
        epsilon: float = 0.10,
        seed: Optional[int] = None,
    ):
        super().__init__(color, name)
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.rng = random.Random(seed)
        self.board_size = None
        self.weights: Dict[str, float] = {}

    def initialize(self, board_size: int) -> bool:
        self.board_size = board_size
        return True

    def get_move(self, board: HexBoard) -> Union[Move, str, None]:
        legal_moves = board.get_empty_cells()
        if not legal_moves:
            return None

        if self.rng.random() < self.epsilon:
            return self.rng.choice(legal_moves)

        return self.get_best_move(board, legal_moves)

    def get_best_move(self, board: HexBoard, legal_moves: Optional[List[Move]] = None) -> Move:
        legal_moves = legal_moves or board.get_empty_cells()
        best_score = -math.inf
        best_moves: List[Move] = []

        for move in legal_moves:
            score = self.get_q_value(board, move)
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return self.rng.choice(best_moves)

    def get_q_value(self, board: HexBoard, move: Move) -> float:
        features = self.extract_features(board, move)
        return sum(self.weights.get(name, 0.0) * value for name, value in features.items())

    def get_value(self, board: HexBoard) -> float:
        legal_moves = board.get_empty_cells()
        if not legal_moves:
            return 0.0
        return max(self.get_q_value(board, move) for move in legal_moves)

    def update(self, board: HexBoard, move: Move, next_board: HexBoard, reward: float, done: bool) -> None:
        features = self.extract_features(board, move)
        prediction = sum(self.weights.get(name, 0.0) * value for name, value in features.items())
        target = reward if done else reward + self.gamma * self.get_value(next_board)
        td_error = target - prediction

        for name, value in features.items():
            self.weights[name] = self.weights.get(name, 0.0) + self.alpha * td_error * value

    def extract_features(self, board: HexBoard, move: Move) -> FeatureVector:
        simulated = self._simulate_move(board, move, self.color)
        opponent = self.color.opponent()
        center = (board.size - 1) / 2.0
        row, col = move
        center_distance = abs(row - center) + abs(col - center)
        max_center_distance = max(1.0, 2.0 * center)

        own_components = self._connected_component_sizes(simulated, self.color)
        opp_components = self._connected_component_sizes(simulated, opponent)

        features = {
            "bias": 1.0,
            "move_count_ratio": simulated.get_move_count() / float(board.size * board.size),
            "center_control": 1.0 - (center_distance / max_center_distance),
            "own_stone_ratio": self._count_cells(simulated, self.color) / float(board.size * board.size),
            "opp_stone_ratio": self._count_cells(simulated, opponent) / float(board.size * board.size),
            "own_edge_coverage": self._edge_coverage(simulated, self.color),
            "opp_edge_coverage": self._edge_coverage(simulated, opponent),
            "own_largest_group": (max(own_components) if own_components else 0) / float(board.size * board.size),
            "opp_largest_group": (max(opp_components) if opp_components else 0) / float(board.size * board.size),
        }

        return features

    def save_weights(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.weights, handle, indent=2, sort_keys=True)

    def load_weights(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as handle:
            self.weights = {key: float(value) for key, value in json.load(handle).items()}

    def clone_for_evaluation(self, color: Color) -> "ApproximateQLearningPlayer":
        clone = ApproximateQLearningPlayer(
            color=color,
            name=f"{self.name} Eval",
            alpha=self.alpha,
            gamma=self.gamma,
            epsilon=0.0,
        )
        clone.weights = dict(self.weights)
        if self.board_size is not None:
            clone.initialize(self.board_size)
        return clone

    @staticmethod
    def _simulate_move(board: HexBoard, move: Move, color: Color) -> HexBoard:
        cloned = HexBoard(board.size)
        cloned.board = dict(board.board)
        cloned.move_history = list(board.move_history)
        cloned.swap_used = board.swap_used
        row, col = move
        result = cloned.make_move(row, col, color)
        if result.value != "success":
            raise ValueError(f"Cannot simulate illegal move {move}: {result.value}")
        return cloned

    @staticmethod
    def _count_cells(board: HexBoard, color: Color) -> int:
        return sum(1 for cell in board.board.values() if cell == color)

    @staticmethod
    def _edge_coverage(board: HexBoard, color: Color) -> float:
        size = board.size
        covered = set()
        if color == Color.RED:
            for col in range(size):
                if board.get_cell(0, col) == color:
                    covered.add(("top", col))
                if board.get_cell(size - 1, col) == color:
                    covered.add(("bottom", col))
        elif color == Color.BLUE:
            for row in range(size):
                if board.get_cell(row, 0) == color:
                    covered.add(("left", row))
                if board.get_cell(row, size - 1) == color:
                    covered.add(("right", row))
        return len(covered) / float(max(1, 2 * size))

    @staticmethod
    def _connected_component_sizes(board: HexBoard, color: Color) -> List[int]:
        visited = set()
        sizes = []
        for position, cell in board.board.items():
            if cell != color or position in visited:
                continue
            sizes.append(ApproximateQLearningPlayer._explore_component(board, position, color, visited))
        return sizes

    @staticmethod
    def _explore_component(board: HexBoard, start: Move, color: Color, visited: set) -> int:
        queue = deque([start])
        visited.add(start)
        size = 0

        while queue:
            row, col = queue.popleft()
            size += 1
            for neighbor in board.get_neighbors(row, col):
                if neighbor in visited:
                    continue
                if board.get_cell(*neighbor) != color:
                    continue
                visited.add(neighbor)
                queue.append(neighbor)

        return size


def play_self_play_episode(red_player: ApproximateQLearningPlayer, blue_player: ApproximateQLearningPlayer, board_size: int) -> Color:
    """
    Train two approximate-Q players through a single self-play game.
    """

    board = HexBoard(board_size)
    players = {
        Color.RED: red_player,
        Color.BLUE: blue_player,
    }
    current_color = Color.RED

    while True:
        player = players[current_color]
        move = player.get_move(board)
        if move is None:
            winner = current_color.opponent()
            break

        next_board = player._simulate_move(board, move, current_color)
        done = next_board.check_win(current_color)
        reward = 1.0 if done else 0.0
        player.update(board, move, next_board, reward, done)

        if done:
            opponent = players[current_color.opponent()]
            opponent.update(board, move, next_board, -1.0, True)
            winner = current_color
            board = next_board
            break

        board = next_board
        current_color = current_color.opponent()

    return winner
