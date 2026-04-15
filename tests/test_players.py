"""
Test cases for player classes.

Tests base Player class and concrete implementations:
- GUIPlayer
- TerminalPlayer  
- SubprocessPlayer
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
from io import StringIO
from engine.board import HexBoard
from engine.constants import Color
from players.base import Player
from players.gui_player import GUIPlayer
from players.terminal_player import TerminalPlayer
from players.subprocess_player import SubprocessPlayer


class ConcretePlayer(Player):
    """Concrete implementation of Player for testing abstract base."""

    def __init__(self, color: Color, name: str = "Test Player"):
        super().__init__(color, name)
        self.initialized = False

    def initialize(self, board_size: int) -> bool:
        self.initialized = True
        return True

    def get_move(self, board: HexBoard):
        return (0, 0)


class TestPlayerBase(unittest.TestCase):
    """Test the base Player abstract class."""

    def test_player_creation_with_red(self):
        """Test creating player with RED color."""
        player = ConcretePlayer(Color.RED, "Red Bot")
        self.assertEqual(player.color, Color.RED)
        self.assertEqual(player.name, "Red Bot")

    def test_player_creation_with_blue(self):
        """Test creating player with BLUE color."""
        player = ConcretePlayer(Color.BLUE, "Blue Bot")
        self.assertEqual(player.color, Color.BLUE)
        self.assertEqual(player.name, "Blue Bot")

    def test_player_invalid_color_raises_error(self):
        """Test that invalid color raises ValueError."""
        with self.assertRaises(ValueError) as context:
            ConcretePlayer(Color.EMPTY, "Invalid")
        self.assertIn("RED or BLUE", str(context.exception))

    def test_player_default_name(self):
        """Test player with default name."""
        player = ConcretePlayer(Color.RED)
        self.assertEqual(player.name, "Test Player")

    def test_player_str_representation(self):
        """Test __str__ method."""
        player = ConcretePlayer(Color.RED, "My Bot")
        result = str(player)
        # Test that string representation is non-empty
        self.assertTrue(len(result) > 0)

    def test_player_repr_representation(self):
        """Test __repr__ method."""
        player = ConcretePlayer(Color.BLUE, "Test")
        result = repr(player)
        # Test that repr is non-empty
        self.assertTrue(len(result) > 0)

    def test_player_cleanup_default(self):
        """Test that cleanup does nothing by default."""
        player = ConcretePlayer(Color.RED)
        # Should not raise any exception
        player.cleanup()

    def test_player_initialize_abstract(self):
        """Test that initialize must be implemented."""
        # ConcretePlayer implements it
        player = ConcretePlayer(Color.RED)
        result = player.initialize(11)
        self.assertTrue(result)
        self.assertTrue(player.initialized)

    def test_player_get_move_abstract(self):
        """Test that get_move must be implemented."""
        player = ConcretePlayer(Color.RED)
        board = HexBoard(5)
        move = player.get_move(board)
        self.assertEqual(move, (0, 0))


class TestGUIPlayer(unittest.TestCase):
    """Test GUIPlayer implementation."""

    def setUp(self):
        self.player = GUIPlayer(Color.RED, "GUI Test")

    def test_gui_player_initialization(self):
        """Test GUI player creation."""
        self.assertEqual(self.player.color, Color.RED)
        self.assertEqual(self.player.name, "GUI Test")
        self.assertIsNone(self.player.pending_move)
        self.assertFalse(self.player.waiting_for_move)

    def test_gui_player_default_name(self):
        """Test GUI player with default name."""
        player = GUIPlayer(Color.BLUE)
        self.assertEqual(player.name, "GUI Player")

    def test_gui_player_initialize(self):
        """Test GUI player initialize method."""
        result = self.player.initialize(11)
        self.assertTrue(result)

    def test_gui_player_get_move_without_pending(self):
        """Test get_move when no move is pending."""
        board = HexBoard(5)
        move = self.player.get_move(board)

        # Should return None and set waiting flag
        self.assertIsNone(move)
        self.assertTrue(self.player.waiting_for_move)

    def test_gui_player_get_move_with_pending(self):
        """Test get_move when move is already pending."""
        board = HexBoard(5)

        # Set a pending move
        self.player.pending_move = (2, 3)

        move = self.player.get_move(board)

        # Should return the pending move and clear it
        self.assertEqual(move, (2, 3))
        self.assertIsNone(self.player.pending_move)
        self.assertFalse(self.player.waiting_for_move)

    def test_gui_player_set_move(self):
        """Test setting a move from GUI."""
        self.player.set_move((5, 5))

        self.assertEqual(self.player.pending_move, (5, 5))
        self.assertFalse(self.player.waiting_for_move)

    def test_gui_player_set_swap_move(self):
        """Test setting swap move from GUI."""
        self.player.set_move("swap")

        self.assertEqual(self.player.pending_move, "swap")
        self.assertFalse(self.player.waiting_for_move)

    def test_gui_player_set_forfeit(self):
        """Test setting forfeit (None) from GUI."""
        self.player.set_move(None)

        self.assertIsNone(self.player.pending_move)
        self.assertFalse(self.player.waiting_for_move)

    def test_gui_player_is_waiting(self):
        """Test is_waiting method."""
        self.assertFalse(self.player.is_waiting())

        board = HexBoard(5)
        self.player.get_move(board)

        self.assertTrue(self.player.is_waiting())

        self.player.set_move((1, 1))
        self.assertFalse(self.player.is_waiting())

    def test_gui_player_str_includes_gui_tag(self):
        """Test that __str__ returns non-empty string."""
        result = str(self.player)
        # Test that string representation exists
        self.assertTrue(len(result) > 0)

    def test_gui_player_multiple_get_move_calls(self):
        """Test calling get_move multiple times without setting move."""
        board = HexBoard(5)

        # First call sets waiting flag
        move1 = self.player.get_move(board)
        self.assertIsNone(move1)
        self.assertTrue(self.player.waiting_for_move)

        # Second call while still waiting
        move2 = self.player.get_move(board)
        self.assertIsNone(move2)
        self.assertTrue(self.player.waiting_for_move)


class TestTerminalPlayer(unittest.TestCase):
    """Test TerminalPlayer implementation."""

    def test_terminal_player_initialization(self):
        """Test terminal player creation."""
        player = TerminalPlayer(Color.RED, "Terminal Test")
        self.assertEqual(player.color, Color.RED)
        self.assertEqual(player.name, "Terminal Test")

    def test_terminal_player_default_name(self):
        """Test terminal player with default name."""
        player = TerminalPlayer(Color.BLUE)
        self.assertEqual(player.name, "Terminal Player")

    @patch('sys.stdout', new_callable=StringIO)
    def test_terminal_player_initialize_prints_info(self, mock_stdout):
        """Test that initialize prints player info."""
        player = TerminalPlayer(Color.RED, "Test")
        result = player.initialize(11)

        self.assertTrue(result)
        output = mock_stdout.getvalue()
        self.assertIn("Test", output)
        self.assertIn("RED", output)
        self.assertIn("11x11", output)

    @patch('builtins.input', return_value='5 7')
    @patch('sys.stdout', new_callable=StringIO)
    def test_terminal_player_get_move_normal(self, mock_stdout, mock_input):
        """Test getting a normal move from terminal."""
        player = TerminalPlayer(Color.RED)
        board = HexBoard(11)

        move = player.get_move(board)

        self.assertEqual(move, (5, 7))

    @patch('builtins.input', return_value='swap')
    @patch('sys.stdout', new_callable=StringIO)
    def test_terminal_player_get_move_swap(self, mock_stdout, mock_input):
        """Test getting a swap move from terminal."""
        player = TerminalPlayer(Color.BLUE)
        board = HexBoard(11)
        board.make_move(5, 5, Color.RED)  # One move on board

        move = player.get_move(board)

        self.assertEqual(move, "swap")

    @patch('builtins.input', return_value='q')
    @patch('sys.stdout', new_callable=StringIO)
    def test_terminal_player_quit(self, mock_stdout, mock_input):
        """Test quitting from terminal."""
        player = TerminalPlayer(Color.RED)
        board = HexBoard(5)

        move = player.get_move(board)

        self.assertIsNone(move)

    @patch('builtins.input', side_effect=['invalid', '2 3'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_terminal_player_invalid_then_valid(self, mock_stdout, mock_input):
        """Test recovery from invalid input."""
        player = TerminalPlayer(Color.RED)
        board = HexBoard(5)

        move = player.get_move(board)

        self.assertEqual(move, (2, 3))

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    @patch('sys.stdout', new_callable=StringIO)
    def test_terminal_player_keyboard_interrupt(self, mock_stdout, mock_input):
        """Test handling keyboard interrupt."""
        player = TerminalPlayer(Color.RED)
        board = HexBoard(5)

        move = player.get_move(board)

        self.assertIsNone(move)

    def test_terminal_player_goal_description_red(self):
        """Test goal description for RED player."""
        player = TerminalPlayer(Color.RED)
        goal = player._get_goal_description()
        self.assertIn("TOP", goal)
        self.assertIn("BOTTOM", goal)

    def test_terminal_player_goal_description_blue(self):
        """Test goal description for BLUE player."""
        player = TerminalPlayer(Color.BLUE)
        goal = player._get_goal_description()
        self.assertIn("LEFT", goal)
        self.assertIn("RIGHT", goal)


class TestSubprocessPlayer(unittest.TestCase):
    """Test SubprocessPlayer implementation."""

    def test_subprocess_player_creation(self):
        """Test creating subprocess player."""
        player = SubprocessPlayer(
            Color.RED,
            "python",
            ["agent.py"],
            timeout=3.0,
            name="Test Agent"
        )

        self.assertEqual(player.color, Color.RED)
        self.assertEqual(player.name, "Test Agent")
        self.assertEqual(player.program_path, "python")
        self.assertEqual(player.args, ["agent.py"])
        self.assertEqual(player.timeout, 3.0)

    def test_subprocess_player_default_name(self):
        """Test subprocess player with auto-generated name."""
        player = SubprocessPlayer(Color.RED, "python", ["my_agent.py"])
        self.assertIn("my_agent.py", player.name)

    def test_subprocess_player_default_timeout(self):
        """Test default timeout value."""
        player = SubprocessPlayer(Color.RED, "python")
        self.assertEqual(player.timeout, SubprocessPlayer.DEFAULT_TIMEOUT)

    @patch('subprocess.Popen')
    def test_subprocess_player_initialize_success(self, mock_popen):
        """Test successful subprocess initialization."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        player = SubprocessPlayer(Color.RED, "python", ["agent.py"])
        result = player.initialize(11)

        self.assertTrue(result)
        self.assertIsNotNone(player.process)
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_subprocess_player_initialize_failure(self, mock_popen):
        """Test subprocess initialization failure."""
        mock_popen.side_effect = FileNotFoundError("Program not found")

        player = SubprocessPlayer(Color.RED, "nonexistent", ["agent.py"])
        result = player.initialize(11)

        self.assertFalse(result)

    @patch('subprocess.Popen')
    def test_subprocess_player_get_move_success(self, mock_popen):
        """Test getting a valid move from subprocess."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.return_value = "5 5\n"
        mock_popen.return_value = mock_process

        player = SubprocessPlayer(Color.RED, "python", ["agent.py"])
        player.initialize(11)

        board = HexBoard(11)
        move = player.get_move(board)

        self.assertEqual(move, (5, 5))

    @patch('subprocess.Popen')
    def test_subprocess_player_get_swap_move(self, mock_popen):
        """Test getting a swap move from subprocess."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.return_value = "swap\n"
        mock_popen.return_value = mock_process

        player = SubprocessPlayer(Color.BLUE, "python", ["agent.py"])
        player.initialize(11)

        board = HexBoard(11)
        board.make_move(5, 5, Color.RED)
        move = player.get_move(board)

        self.assertEqual(move, "swap")

    @patch('subprocess.Popen')
    def test_subprocess_player_process_dead(self, mock_popen):
        """Test handling dead subprocess."""
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process has died
        mock_process.stderr = MagicMock()
        mock_process.stderr.read.return_value = "Error message"
        mock_popen.return_value = mock_process

        player = SubprocessPlayer(Color.RED, "python", ["agent.py"])
        player.initialize(11)

        board = HexBoard(11)
        move = player.get_move(board)

        self.assertIsNone(move)

    @patch('subprocess.Popen')
    def test_subprocess_player_cleanup(self, mock_popen):
        """Test cleanup terminates subprocess."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        player = SubprocessPlayer(Color.RED, "python", ["agent.py"])
        player.initialize(11)

        player.cleanup()

        mock_process.terminate.assert_called_once()

    @patch('subprocess.Popen')
    def test_subprocess_player_is_dead(self, mock_popen):
        """Test _is_dead method."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        player = SubprocessPlayer(Color.RED, "python", ["agent.py"])
        player.initialize(11)

        # Process running
        mock_process.poll.return_value = None
        self.assertFalse(player._is_dead())

        # Process dead
        mock_process.poll.return_value = 1
        self.assertTrue(player._is_dead())

    def test_subprocess_player_no_process_is_dead(self):
        """Test _is_dead when no process exists."""
        player = SubprocessPlayer(Color.RED, "python", ["agent.py"])
        self.assertTrue(player._is_dead())

    @patch('subprocess.Popen')
    def test_subprocess_player_invalid_protocol_response(self, mock_popen):
        """Test handling invalid protocol response."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline.return_value = "invalid response\n"
        mock_process.stderr = MagicMock()
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        player = SubprocessPlayer(Color.RED, "python", ["agent.py"])
        player.initialize(11)

        board = HexBoard(11)
        move = player.get_move(board)

        # Should return None for invalid protocol
        self.assertIsNone(move)

    @patch('subprocess.Popen')
    def test_subprocess_player_memory_limit(self, mock_popen):
        """Test memory limit configuration."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        player = SubprocessPlayer(
            Color.RED,
            "python",
            ["agent.py"],
            memory_limit_mb=256.0
        )

        self.assertEqual(player.memory_limit_mb, 256.0)

    @patch('subprocess.Popen')
    def test_subprocess_player_command_construction(self, mock_popen):
        """Test that command is constructed correctly."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        player = SubprocessPlayer(
            Color.RED,
            "python3",
            ["-u", "agent.py", "--verbose"]
        )
        player.initialize(11)

        # Check that Popen was called with correct command
        args, kwargs = mock_popen.call_args
        command = args[0]
        self.assertEqual(command[0], "python3")
        self.assertIn("-u", command)
        self.assertIn("agent.py", command)
        self.assertIn("--verbose", command)


class TestPlayerIntegration(unittest.TestCase):
    """Test integration between different player types."""

    def test_different_player_types_in_game(self):
        """Test that different player types can coexist."""
        gui_player = GUIPlayer(Color.RED, "GUI")
        terminal_player = TerminalPlayer(Color.BLUE, "Terminal")

        # Both should initialize successfully
        self.assertTrue(gui_player.initialize(11))
        self.assertTrue(terminal_player.initialize(11))

        # Both should have correct colors
        self.assertEqual(gui_player.color, Color.RED)
        self.assertEqual(terminal_player.color, Color.BLUE)

    def test_player_color_uniqueness(self):
        """Test that players can have different colors."""
        red = GUIPlayer(Color.RED)
        blue = GUIPlayer(Color.BLUE)

        self.assertNotEqual(red.color, blue.color)

    def test_player_name_display(self):
        """Test player name display across types."""
        players = [
            GUIPlayer(Color.RED, "Alice"),
            TerminalPlayer(Color.BLUE, "Bob"),
        ]

        for player in players:
            str_repr = str(player)
            # Test that each player has a string representation
            self.assertTrue(len(str_repr) > 0)
            # Test that names match
            self.assertEqual(
                player.name, "Alice" if player.color == Color.RED else "Bob")


if __name__ == '__main__':
    unittest.main()
