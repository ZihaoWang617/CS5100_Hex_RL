"""
Protocol definition for stdin/stdout communication with student agents.

The engine sends ONE line with board state, agent responds with ONE line containing move.

Format: <SIZE> <YOUR_COLOR> <MOVES>
Example: 11 RED 5:5:B,6:6:R,7:7:B
Response: 8 8

Students parse the input and output their move.
"""

from typing import Tuple, Union
from .board import HexBoard
from .constants import Color


class ProtocolError(Exception):
    """Raised when protocol parsing or validation fails."""
    pass


class Protocol:
    """
    Handles encoding and decoding of protocol messages for the engine.
    """

    @staticmethod
    def encode_board(board: HexBoard, player_color: Color) -> str:
        """
        Create one-line board state message to send to student agent.

        Format: <SIZE> <YOUR_COLOR> <MOVES>
        Example: 11 RED 5:5:B,6:6:R

        Args:
            board: Current board state
            player_color: The color of the player receiving this message

        Returns:
            Single-line protocol message
        """
        moves = []
        for (row, col), cell_color in board.board.items():
            if cell_color != Color.EMPTY:
                color_char = 'R' if cell_color == Color.RED else 'B'
                moves.append(f"{row}:{col}:{color_char}")

        moves_str = ','.join(moves) if moves else ''
        return f"{board.size} {player_color.name} {moves_str}\n"

    @staticmethod
    def decode_move(line: str) -> Union[Tuple[int, int], str]:
        """
        Parse move response from agent.

        Expected format: <ROW> <COL> or 'swap'
        Example: 5 5
        Example: swap

        Args:
            line: Input line from agent

        Returns:
            Tuple of (row, col) for normal move, or "swap" string for swap move

        Raises:
            ProtocolError: If format is invalid
        """
        line = line.strip()

        if not line:
            raise ProtocolError("Empty move string")

        # Check if it's a swap move
        if line.lower() == "swap":
            return "swap"

        parts = line.split()

        if len(parts) != 2:
            raise ProtocolError(
                f"Invalid move format: '{line}'. Expected: <row> <col> or 'swap'")

        try:
            row = int(parts[0])
            col = int(parts[1])
            return (row, col)
        except ValueError as e:
            raise ProtocolError(
                f"Invalid move coordinates: '{line}'. Must be integers.") from e
