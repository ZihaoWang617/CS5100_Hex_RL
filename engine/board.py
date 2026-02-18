"""
Hex board representation, move validation, and win detection.
"""

from collections import deque
from typing import Optional, Set, Tuple, List
from .constants import Color, MoveResult, HEX_DIRECTIONS, DEFAULT_BOARD_SIZE


class HexBoard:
    """
    Represents a Hex game board.

    Coordinate system:
    - (row, col) where both start at 0
    - row increases downward, col increases rightward
    - RED connects top (row=0) to bottom (row=size-1)
    - BLUE connects left (col=0) to right (col=size-1)
    """

    def __init__(self, size: int = DEFAULT_BOARD_SIZE):
        """
        Initialize an empty Hex board.

        Args:
            size: Board dimension (size x size)
        """
        if size < 3:
            raise ValueError("Board size must be at least 3")
        if size > 26:
            raise ValueError("Board size must be at most 26")

        self.size = size
        # Store board state as dict: (row, col) -> Color
        self.board = {}
        for row in range(size):
            for col in range(size):
                self.board[(row, col)] = Color.EMPTY

        self.move_history = []  # List of (row, col, color) tuples
        # Track if swap has been used (can only swap once)
        self.swap_used = False

    def is_valid_position(self, row: int, col: int) -> bool:
        """Check if a position is within board bounds."""
        return 0 <= row < self.size and 0 <= col < self.size

    def get_cell(self, row: int, col: int) -> Color:
        """Get the color at a specific cell."""
        if not self.is_valid_position(row, col):
            raise ValueError(f"Position ({row}, {col}) is out of bounds")
        return self.board[(row, col)]

    def is_empty(self, row: int, col: int) -> bool:
        """Check if a cell is empty."""
        return self.get_cell(row, col) == Color.EMPTY

    def make_move(self, row: int, col: int, color: Color) -> MoveResult:
        """
        Place a stone on the board.

        Args:
            row: Row index
            col: Column index
            color: Color of the stone to place

        Returns:
            MoveResult indicating success or failure reason
        """
        if color == Color.EMPTY:
            return MoveResult.INVALID_FORMAT

        if not self.is_valid_position(row, col):
            return MoveResult.OUT_OF_BOUNDS

        if not self.is_empty(row, col):
            return MoveResult.CELL_OCCUPIED

        # Make the move
        self.board[(row, col)] = color
        self.move_history.append((row, col, color))

        return MoveResult.SUCCESS

    def swap_move(self) -> MoveResult:
        """
        Execute a swap move (pie rule).

        A swap move can only be performed when there is exactly one move on the board
        and swap has not been used yet.
        The move's position is swapped (row <-> col) and the color is changed to the opponent's color.

        For example:
        - If RED placed at (4, 8), after swap there will be BLUE at (8, 4)
        - If BLUE placed at (1, 7), after swap there will be RED at (7, 1)

        Returns:
            MoveResult.SUCCESS if swap was successful
            MoveResult.SWAP_NOT_ALLOWED if swap has already been used or there isn't exactly one move
        """
        # Check if swap has already been used
        if self.swap_used:
            return MoveResult.SWAP_NOT_ALLOWED

        # Check if there's exactly one move on the board
        if len(self.move_history) != 1:
            return MoveResult.SWAP_NOT_ALLOWED

        # Get the first (and only) move
        row, col, color = self.move_history[0]

        # Calculate the swapped position and color
        swapped_row = col
        swapped_col = row
        swapped_color = color.opponent()

        # Clear the original position
        self.board[(row, col)] = Color.EMPTY

        # Place the swapped move
        self.board[(swapped_row, swapped_col)] = swapped_color

        # Update move history
        self.move_history[0] = (swapped_row, swapped_col, swapped_color)

        # Mark swap as used
        self.swap_used = True

        return MoveResult.SUCCESS

    def undo_move(self) -> bool:
        """
        Undo the last move.

        Returns:
            True if a move was undone, False if no moves to undo
        """
        if not self.move_history:
            return False

        row, col, _ = self.move_history.pop()
        self.board[(row, col)] = Color.EMPTY
        return True

    def get_neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        """
        Get valid neighboring positions.

        Args:
            row: Row index
            col: Column index

        Returns:
            List of (row, col) tuples for valid neighbors
        """
        neighbors = []
        for dr, dc in HEX_DIRECTIONS:
            new_row, new_col = row + dr, col + dc
            if self.is_valid_position(new_row, new_col):
                neighbors.append((new_row, new_col))
        return neighbors

    def check_win(self, color: Color) -> bool:
        """
        Check if the specified color has won.

        Uses BFS to find a path connecting the appropriate sides:
        - RED: top to bottom
        - BLUE: left to right

        Args:
            color: Color to check for win

        Returns:
            True if the color has a winning path
        """
        if color == Color.EMPTY:
            return False

        if color == Color.RED:
            return self._check_red_win()
        else:  # Color.BLUE
            return self._check_blue_win()

    def _check_red_win(self) -> bool:
        """Check if RED has connected top to bottom."""
        # Start from all RED cells in the top row
        queue = deque()
        visited = set()

        for col in range(self.size):
            if self.board[(0, col)] == Color.RED:
                queue.append((0, col))
                visited.add((0, col))

        # BFS to find path to bottom row
        while queue:
            row, col = queue.popleft()

            # Check if we reached the bottom row
            if row == self.size - 1:
                return True

            # Explore neighbors
            for neighbor_row, neighbor_col in self.get_neighbors(row, col):
                if (neighbor_row, neighbor_col) not in visited:
                    if self.board[(neighbor_row, neighbor_col)] == Color.RED:
                        visited.add((neighbor_row, neighbor_col))
                        queue.append((neighbor_row, neighbor_col))

        return False

    def _check_blue_win(self) -> bool:
        """Check if BLUE has connected left to right."""
        # Start from all BLUE cells in the left column
        queue = deque()
        visited = set()

        for row in range(self.size):
            if self.board[(row, 0)] == Color.BLUE:
                queue.append((row, 0))
                visited.add((row, 0))

        # BFS to find path to right column
        while queue:
            row, col = queue.popleft()

            # Check if we reached the right column
            if col == self.size - 1:
                return True

            # Explore neighbors
            for neighbor_row, neighbor_col in self.get_neighbors(row, col):
                if (neighbor_row, neighbor_col) not in visited:
                    if self.board[(neighbor_row, neighbor_col)] == Color.BLUE:
                        visited.add((neighbor_row, neighbor_col))
                        queue.append((neighbor_row, neighbor_col))

        return False

    def get_winner(self) -> Optional[Color]:
        """
        Check if there is a winner.

        Returns:
            Color.RED or Color.BLUE if that color won, None otherwise
        """
        if self.check_win(Color.RED):
            return Color.RED
        if self.check_win(Color.BLUE):
            return Color.BLUE
        return None

    def is_full(self) -> bool:
        """Check if the board is completely filled."""
        return all(cell != Color.EMPTY for cell in self.board.values())

    def get_empty_cells(self) -> List[Tuple[int, int]]:
        """Get list of all empty cells."""
        return [(row, col) for (row, col), color in self.board.items()
                if color == Color.EMPTY]

    def get_move_count(self) -> int:
        """Get the total number of moves made."""
        return len(self.move_history)

    def clone(self) -> 'HexBoard':
        """Create a deep copy of the board."""
        new_board = HexBoard(self.size)
        new_board.board = self.board.copy()
        new_board.move_history = self.move_history.copy()
        new_board.swap_used = self.swap_used
        return new_board

    def to_string(self) -> str:
        """
        Create a string representation of the board.

        Returns:
            Multi-line string showing the board state
        """
        lines = []
        lines.append("  " + " ".join(str(i) for i in range(self.size)))

        for row in range(self.size):
            indent = " " * row
            row_str = f"{row:2d} {indent}"

            for col in range(self.size):
                cell = self.board[(row, col)]
                if cell == Color.RED:
                    row_str += "R "
                elif cell == Color.BLUE:
                    row_str += "B "
                else:
                    row_str += ". "

            lines.append(row_str)

        return "\n".join(lines)

    def __str__(self) -> str:
        return self.to_string()

    def to_dict(self) -> dict:
        """
        Export board state as dictionary for serialization.

        Returns:
            Dictionary containing board state
        """
        return {
            'size': self.size,
            'board': {f"{r},{c}": cell.value for (r, c), cell in self.board.items()},
            'move_history': [(r, c, color.value) for r, c, color in self.move_history],
            'swap_used': self.swap_used
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'HexBoard':
        """
        Create a board from dictionary representation.

        Args:
            data: Dictionary containing board state

        Returns:
            HexBoard instance
        """
        board = cls(data['size'])

        # Restore board state
        for pos_str, color_value in data['board'].items():
            r, c = map(int, pos_str.split(','))
            board.board[(r, c)] = Color(color_value)

        # Restore move history
        board.move_history = [(r, c, Color(color_value))
                              for r, c, color_value in data['move_history']]

        # Restore swap_used flag (default to False for backward compatibility)
        board.swap_used = data.get('swap_used', False)

        return board
