"""
Simple terminal-based player for testing and debugging.

Allows a human to play through terminal input/output.
"""

from typing import Tuple, Optional, Union
from engine.board import HexBoard
from engine.constants import Color
from .base import Player


class TerminalPlayer(Player):
    """
    Interactive terminal player for testing.

    Displays the board and prompts for moves via stdin/stdout.
    Useful for manual testing and debugging.
    """

    def __init__(self, color: Color, name: str = "Terminal Player"):
        """
        Initialize terminal player.

        Args:
            color: Player's color
            name: Display name
        """
        super().__init__(color, name)
        self.board_size = None

    def initialize(self, board_size: int) -> bool:
        """
        Initialize with board size.

        Args:
            board_size: Size of the game board

        Returns:
            True (always succeeds)
        """
        self.board_size = board_size
        print(f"\n{'='*60}")
        print(f"  {self.name} initialized")
        print(f"  Color: {self.color.name}")
        print(f"  Board Size: {board_size}x{board_size}")
        print(f"  Goal: {self._get_goal_description()}")
        print(f"{'='*60}\n")
        return True

    def get_move(self, board: HexBoard) -> Union[Tuple[int, int], str, None]:
        """
        Prompt user for a move via terminal.

        Args:
            board: Current board state

        Returns:
            Tuple of (row, col) for normal move, "swap" for swap move, or None if input fails
        """
        # Display current board
        print(f"\n{board.to_string()}")
        print(f"\n{self.name}'s turn ({self.color.name})")

        # Show empty cells for convenience
        empty_cells = board.get_empty_cells()
        print(f"Available moves: {len(empty_cells)} cells")

        # Check if swap is available
        move_count = board.get_move_count()
        if move_count == 1 and not board.swap_used:
            print("\n*** SWAP AVAILABLE: You can type 'swap' to use the pie rule ***")

        # Prompt for input
        while True:
            try:
                user_input = input(
                    "Enter move (row col), 'swap', or 'q' to quit: ").strip()

                if user_input.lower() in ['q', 'quit', 'exit']:
                    print("Player quit.")
                    return None

                # Check for swap move
                if user_input.lower() == 'swap':
                    if move_count == 1 and not board.swap_used:
                        print("Executing swap move...")
                        return "swap"
                    elif board.swap_used:
                        print("Swap has already been used!")
                        continue
                    else:
                        print("Swap is only allowed after exactly one move!")
                        continue

                # Parse input - support multiple formats
                parts = user_input.replace(',', ' ').replace(
                    '(', '').replace(')', '').split()

                if len(parts) != 2:
                    print("Invalid format. Please enter: row col (e.g., 5 7) or 'swap'")
                    continue

                row = int(parts[0])
                col = int(parts[1])

                # Basic validation
                if not (0 <= row < board.size and 0 <= col < board.size):
                    print(
                        f"Out of bounds! Row and col must be 0-{board.size-1}")
                    continue

                if not board.is_empty(row, col):
                    print(f"Cell ({row}, {col}) is already occupied!")
                    continue

                return (row, col)

            except ValueError:
                print("Invalid input. Please enter two integers.")
            except KeyboardInterrupt:
                print("\nPlayer interrupted.")
                return None
            except Exception as e:
                print(f"Error: {e}")
                return None

    def _get_goal_description(self) -> str:
        """Get a description of the player's goal."""
        if self.color == Color.RED:
            return "Connect TOP to BOTTOM"
        elif self.color == Color.BLUE:
            return "Connect LEFT to RIGHT"
        return "Unknown"
