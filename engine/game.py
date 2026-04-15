"""
Game controller for Hex game.

Manages game loop, turn management, move validation, and win detection.
"""

import time
from typing import Optional, List, Dict, Any
from enum import Enum
from .board import HexBoard
from .constants import Color, GameStatus, MoveResult, DEFAULT_BOARD_SIZE


class LogLevel(Enum):
    """Log message severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class GameEvent:
    """Represents a game event for logging."""

    def __init__(self, level: LogLevel, message: str):
        self.timestamp = time.time()
        self.level = level
        self.message = message


class GameController:
    """
    Controls the Hex game flow.

    Responsibilities:
    - Manage game loop and turn order
    - Validate moves with retry logic
    - Track errors and enforce limits
    - Detect game end conditions
    - Log all game events
    """

    # Configuration
    MAX_INVALID_MOVES = 3  # Max retries per turn
    MAX_TOTAL_ERRORS = 3  # Max total errors per player before forfeit

    def __init__(self, board_size: int = DEFAULT_BOARD_SIZE):
        """
        Initialize game controller.

        Args:
            board_size: Size of the game board
        """
        self.board_size = board_size
        self.board = HexBoard(board_size)

        # Game state
        self.status = GameStatus.ONGOING
        self.winner = None
        self.current_turn = 0

        # Players (will be set by start_game)
        self.red_player = None
        self.blue_player = None
        self.current_player = None

        # Error tracking
        self.player_errors = {Color.RED: 0, Color.BLUE: 0}

        # Event log
        self.events: List[GameEvent] = []
        self.move_history: List[Dict[str, Any]] = []

    def log_event(self, level: LogLevel, message: str):
        """Log a game event."""
        event = GameEvent(level, message)
        self.events.append(event)

    def start_game(self, red_player, blue_player) -> bool:
        """
        Start a new game with the given players.

        Args:
            red_player: Player object for RED
            blue_player: Player object for BLUE

        Returns:
            True if game started successfully
        """
        self.red_player = red_player
        self.blue_player = blue_player

        # Initialize players
        self.log_event(LogLevel.INFO, f"Initializing {red_player.name}...")
        if not red_player.initialize(self.board_size):
            self.log_event(LogLevel.CRITICAL,
                           f"{red_player.name} failed to initialize")
            return False

        self.log_event(LogLevel.INFO, f"Initializing {blue_player.name}...")
        if not blue_player.initialize(self.board_size):
            self.log_event(LogLevel.CRITICAL,
                           f"{blue_player.name} failed to initialize")
            return False

        # RED always goes first
        self.current_player = red_player

        self.log_event(LogLevel.INFO,
                       f"Game started - {red_player.name} vs {blue_player.name}")

        return True

    def play_turn(self) -> bool:
        """
        Execute one turn of the game.

        Returns:
            True if game should continue, False if game ended
        """
        if self.status != GameStatus.ONGOING:
            return False

        self.current_turn += 1
        player = self.current_player

        self.log_event(LogLevel.INFO,
                       f"Turn {self.current_turn}: {player.name}'s turn")

        # Try to get a valid move with retries
        move = self._get_valid_move(player)

        if move is None:
            # Player forfeited or exceeded error limit
            self._handle_forfeit(player)
            return False

        # Check if it's a swap move
        if move == "swap":
            result = self.board.swap_move()

            if result != MoveResult.SUCCESS:
                # Swap not allowed
                self.log_event(LogLevel.ERROR,
                               f"Swap move not allowed: {result.value}")
                self._record_error(player)
                self._handle_forfeit(player)
                return False

            # Log successful swap
            self.log_event(LogLevel.INFO,
                           f"{player.name} executed swap move")

            self.move_history.append({
                'turn': self.current_turn,
                'player': player.name,
                'color': player.color.name,
                'move': 'swap'
            })
        else:
            # Normal move
            row, col = move

            # Make the move (already validated in _get_valid_move)
            result = self.board.make_move(row, col, player.color)

            if result != MoveResult.SUCCESS:
                # This shouldn't happen, but handle it
                self.log_event(LogLevel.ERROR,
                               f"Unexpected move validation failure: {result.value}")
                self._handle_forfeit(player)
                return False

            # Log successful move
            self.log_event(LogLevel.INFO,
                           f"{player.name} played {move}")

            self.move_history.append({
                'turn': self.current_turn,
                'player': player.name,
                'color': player.color.name,
                'move': move
            })

        # Check for win
        if self.board.check_win(player.color):
            self._handle_win(player)
            return False

        # Switch to next player
        self._switch_player()

        return True

    def _get_valid_move(self, player):
        """
        Get a valid move from player with retry logic.

        Args:
            player: The player to get move from

        Returns:
            Valid (row, col) tuple, "swap" string, or None if player forfeits
        """
        for attempt in range(1, self.MAX_INVALID_MOVES + 1):
            # Get move from player
            try:
                move = player.get_move(self.board)
            except Exception as e:
                self.log_event(LogLevel.ERROR,
                               f"{player.name} crashed: {e}")
                self._record_error(player)
                return None

            if move is None:
                self.log_event(LogLevel.ERROR,
                               f"{player.name} returned None (forfeit)")
                return None

            # Check if it's a swap move
            if move == "swap":
                # Validate swap is allowed (exactly one move on board and swap not used)
                if len(self.board.move_history) == 1 and not self.board.swap_used:
                    return "swap"
                else:
                    validation_result = MoveResult.SWAP_NOT_ALLOWED
            else:
                # Validate normal move
                row, col = move
                validation_result = self._validate_move(row, col)

                if validation_result == MoveResult.SUCCESS:
                    # Valid move!
                    if attempt > 1:
                        self.log_event(LogLevel.INFO,
                                       f"{player.name} provided valid move after {attempt} attempts")
                    return move

            # Invalid move - log and potentially retry
            self._record_error(player)

            self.log_event(LogLevel.WARNING,
                           f"{player.name} invalid move {move}: {validation_result.value} "
                           f"(attempt {attempt}/{self.MAX_INVALID_MOVES})")

            # Check if player exceeded total error limit
            if self.player_errors[player.color] >= self.MAX_TOTAL_ERRORS:
                self.log_event(LogLevel.CRITICAL,
                               f"{player.name} exceeded maximum total errors")
                return None

        # Exceeded retry limit
        self.log_event(LogLevel.ERROR,
                       f"{player.name} exceeded maximum invalid moves per turn")
        return None

    def _validate_move(self, row: int, col: int) -> MoveResult:
        """Validate a move."""
        if not self.board.is_valid_position(row, col):
            return MoveResult.OUT_OF_BOUNDS

        if not self.board.is_empty(row, col):
            return MoveResult.CELL_OCCUPIED

        return MoveResult.SUCCESS

    def _record_error(self, player):
        """Track player errors."""
        self.player_errors[player.color] += 1

    def _handle_forfeit(self, player):
        """Handle player forfeit."""
        self.status = GameStatus.ERROR
        opponent = self._get_opponent(player)
        self.winner = opponent.color

        self.log_event(LogLevel.CRITICAL,
                       f"{player.name} FORFEITED - {opponent.name} wins")

    def _handle_win(self, player):
        """Handle player victory."""
        self.status = GameStatus.RED_WIN if player.color == Color.RED else GameStatus.BLUE_WIN
        self.winner = player.color

        self.log_event(LogLevel.INFO,
                       f"{player.name} WINS!")

    def _switch_player(self):
        """Switch to the other player."""
        if self.current_player == self.red_player:
            self.current_player = self.blue_player
        else:
            self.current_player = self.red_player

    def _get_opponent(self, player):
        """Get the opponent of a player."""
        return self.blue_player if player == self.red_player else self.red_player

    def get_game_summary(self) -> Dict[str, Any]:
        """Get summary of the game."""
        return {
            'status': self.status.value,
            'winner': self.winner.name if self.winner else None,
            'total_turns': self.current_turn,
            'red_player': self.red_player.name if self.red_player else None,
            'blue_player': self.blue_player.name if self.blue_player else None,
            'red_errors': self.player_errors[Color.RED],
            'blue_errors': self.player_errors[Color.BLUE],
            'move_count': len(self.move_history)
        }
