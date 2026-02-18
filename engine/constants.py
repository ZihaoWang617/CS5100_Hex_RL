"""
Game constants for Hex game framework.
"""

from enum import Enum

# Player colors


class Color(Enum):
    EMPTY = 0
    RED = 1
    BLUE = 2

    def __str__(self):
        return self.name

    def opponent(self):
        """Get the opponent's color."""
        if self == Color.RED:
            return Color.BLUE
        elif self == Color.BLUE:
            return Color.RED
        return Color.EMPTY

# Game status codes


class GameStatus(Enum):
    ONGOING = "ongoing"
    RED_WIN = "red_win"
    BLUE_WIN = "blue_win"
    DRAW = "draw"  # Shouldn't happen in Hex but included for completeness
    ERROR = "error"  # Illegal move or crash

    def __str__(self):
        return self.value

# Move result codes


class MoveResult(Enum):
    SUCCESS = "success"
    INVALID_FORMAT = "invalid_format"
    OUT_OF_BOUNDS = "out_of_bounds"
    CELL_OCCUPIED = "cell_occupied"
    WRONG_TURN = "wrong_turn"
    GAME_OVER = "game_over"
    SWAP_NOT_ALLOWED = "swap_not_allowed"

    def __str__(self):
        return self.value


# Default board sizes
DEFAULT_BOARD_SIZE = 11
MIN_BOARD_SIZE = 3
MAX_BOARD_SIZE = 26

# Resource limits (defaults)
DEFAULT_TIME_LIMIT = 5.0  # seconds per move (wall time)
DEFAULT_CPU_LIMIT = 5.0   # seconds per move (CPU time)
DEFAULT_MEMORY_LIMIT = 512  # MB

# Hex directions (6 neighbors in hex grid)
# For coordinate system where row increases down, col increases right
HEX_DIRECTIONS = [
    (-1, 0),   # top
    (-1, 1),   # top-right
    (0, 1),    # right
    (1, 0),    # bottom
    (1, -1),   # bottom-left
    (0, -1),   # left
]
