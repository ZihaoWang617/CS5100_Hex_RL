"""
Random baseline player for Hex.
"""

import random
from typing import Optional, Tuple, Union

from engine.board import HexBoard
from engine.constants import Color
from players.base import Player


class RandomPlayer(Player):
    """Choose a uniformly random legal move."""

    def __init__(self, color: Color, name: str = "Random Player", seed: Optional[int] = None):
        super().__init__(color, name)
        self.rng = random.Random(seed)
        self.board_size = None

    def initialize(self, board_size: int) -> bool:
        self.board_size = board_size
        return True

    def get_move(self, board: HexBoard) -> Union[Tuple[int, int], str, None]:
        legal_moves = board.get_empty_cells()
        if not legal_moves:
            return None
        return self.rng.choice(legal_moves)
