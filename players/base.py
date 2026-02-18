"""
Abstract base classes for Hex game players.

Defines the minimal interface that all player implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, Union
from engine.board import HexBoard
from engine.constants import Color


class Player(ABC):
    """
    Abstract base class for all player implementations.

    This represents any entity that can play Hex: human, AI, or external program.
    The game controller handles all validation, retries, and game end logic.
    Players simply respond to board states with moves.
    """

    def __init__(self, color: Color, name: str = "Player"):
        """
        Initialize a player.

        Args:
            color: The player's color (RED or BLUE)
            name: Display name for the player
        """
        if color not in [Color.RED, Color.BLUE]:
            raise ValueError("Player color must be RED or BLUE")

        self.color = color
        self.name = name

    @abstractmethod
    def initialize(self, board_size: int) -> bool:
        """
        Initialize the player with game configuration.
        Called once before the game starts.

        Args:
            board_size: Size of the game board

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    def get_move(self, board: HexBoard) -> Union[Tuple[int, int], str, None]:
        """
        Request a move from the player given the current board state.

        This is the core method that all players must implement.
        The player should analyze the board and return their chosen move.

        Args:
            board: Current board state

        Returns:
            Tuple of (row, col) for a normal move,
            "swap" string for a swap move (pie rule),
            or None if player forfeits/fails

        Note:
            - Game controller will validate the move
            - Game controller handles retries for invalid moves
            - Returning None indicates forfeit (crash, timeout, etc.)
            - Swap move is only valid when there's exactly one move on the board
        """
        pass

    def cleanup(self) -> None:
        """
        Clean up resources when player is finished.
        Called when game ends or player is removed.

        Override this to close files, processes, network connections, etc.
        Default implementation does nothing.
        """
        pass

    def __str__(self) -> str:
        return f"{self.name} ({self.color.name})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} color={self.color.name}>"
