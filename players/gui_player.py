"""
GUI-based player for Hex game.

Allows a human to play through the graphical interface by clicking on cells.
"""

from typing import Tuple, Optional, Union
from engine.board import HexBoard
from engine.constants import Color
from .base import Player


class GUIPlayer(Player):
    """
    Interactive GUI player.

    Receives moves through clicks on the graphical interface.
    Works with TkinterView to handle user input.
    """

    def __init__(self, color: Color, name: str = "GUI Player"):
        """
        Initialize GUI player.

        Args:
            color: Player's color
            name: Display name
        """
        super().__init__(color, name)
        self.pending_move = None
        self.waiting_for_move = False

    def initialize(self, board_size: int) -> bool:
        """
        Initialize with board size.

        Args:
            board_size: Size of the game board

        Returns:
            True (always succeeds)
        """
        return True

    def get_move(self, board: HexBoard) -> Union[Tuple[int, int], str, None]:
        """
        Wait for user to click on the GUI.

        This method sets a flag and waits for the GUI to provide a move
        through the set_move() method.

        Args:
            board: Current board state

        Returns:
            Tuple of (row, col) for normal move, "swap" for swap move, or None if player forfeits
        """
        # If a move is already pending (user already clicked), return it
        if self.pending_move is not None:
            move = self.pending_move
            self.pending_move = None
            self.waiting_for_move = False
            return move

        # Otherwise, initiate waiting for user input
        if not self.waiting_for_move:
            self.waiting_for_move = True

        # Return None to indicate we're still waiting
        # The game loop will handle the waiting
        return None

    def set_move(self, move: Union[Tuple[int, int], str, None]):
        """
        Set the move chosen by the user through GUI.

        This is called by the TkinterView when user clicks on a cell.

        Args:
            move: The move to set (row, col), "swap", or None for forfeit
        """
        self.pending_move = move
        self.waiting_for_move = False

    def is_waiting(self) -> bool:
        """Check if player is currently waiting for input."""
        return self.waiting_for_move

    def __str__(self) -> str:
        return f"{self.name} ({self.color.name}) [GUI]"
