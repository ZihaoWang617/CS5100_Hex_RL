"""
Hex game engine module.
"""

from .board import HexBoard
from .constants import (
    Color,
    GameStatus,
    MoveResult,
    DEFAULT_BOARD_SIZE,
    MIN_BOARD_SIZE,
    MAX_BOARD_SIZE,
    DEFAULT_TIMEOUT,
    DEFAULT_MEMORY_LIMIT,
    HEX_DIRECTIONS,
    BOARD_SIZE_TIMEOUTS,
    get_timeout_for_board_size
)

__all__ = [
    'HexBoard',
    'Color',
    'GameStatus',
    'MoveResult',
    'DEFAULT_BOARD_SIZE',
    'MIN_BOARD_SIZE',
    'MAX_BOARD_SIZE',
    'DEFAULT_TIMEOUT',
    'DEFAULT_MEMORY_LIMIT',
    'HEX_DIRECTIONS',
    'BOARD_SIZE_TIMEOUTS',
    'get_timeout_for_board_size'
]
