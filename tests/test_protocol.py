"""
Test cases for Protocol class.

Tests encoding board state and decoding move responses for
stdin/stdout communication with agents.
"""

import unittest
from engine.protocol import Protocol, ProtocolError
from engine.board import HexBoard
from engine.constants import Color


class TestEncodeBoard(unittest.TestCase):
    """Test board state encoding."""

    def test_encode_empty_board(self):
        """Test encoding an empty board."""
        board = HexBoard(5)
        result = Protocol.encode_board(board, Color.RED)

        # Should be: "5 RED \n" with empty moves
        self.assertEqual(result, "5 RED \n")

    def test_encode_board_with_color_name(self):
        """Test that color is encoded as name (RED or BLUE)."""
        board = HexBoard(11)

        red_result = Protocol.encode_board(board, Color.RED)
        self.assertIn("RED", red_result)

        blue_result = Protocol.encode_board(board, Color.BLUE)
        self.assertIn("BLUE", blue_result)

    def test_encode_board_with_single_move(self):
        """Test encoding board with one move."""
        board = HexBoard(5)
        board.make_move(2, 3, Color.RED)

        result = Protocol.encode_board(board, Color.BLUE)

        # Should contain size, color, and move
        self.assertIn("5", result)
        self.assertIn("BLUE", result)
        self.assertIn("2:3:R", result)

    def test_encode_board_with_multiple_moves(self):
        """Test encoding board with multiple moves."""
        board = HexBoard(7)
        board.make_move(0, 0, Color.RED)
        board.make_move(1, 1, Color.BLUE)
        board.make_move(2, 2, Color.RED)

        result = Protocol.encode_board(board, Color.RED)

        # Should contain all moves
        self.assertIn("0:0:R", result)
        self.assertIn("1:1:B", result)
        self.assertIn("2:2:R", result)

        # Moves should be comma-separated
        self.assertIn(",", result)

    def test_encode_board_correct_format(self):
        """Test that encoded board follows correct format."""
        board = HexBoard(11)
        board.make_move(5, 5, Color.BLUE)
        board.make_move(6, 6, Color.RED)

        result = Protocol.encode_board(board, Color.RED)

        # Should start with size and color
        self.assertTrue(result.startswith("11 RED "))

        # Should end with newline
        self.assertTrue(result.endswith("\n"))

    def test_encode_board_move_format(self):
        """Test that moves are encoded as row:col:color."""
        board = HexBoard(5)
        board.make_move(3, 4, Color.RED)

        result = Protocol.encode_board(board, Color.BLUE)

        # Should contain move in format row:col:R
        self.assertIn("3:4:R", result)

    def test_encode_board_red_as_r(self):
        """Test that RED stones are encoded as 'R'."""
        board = HexBoard(5)
        board.make_move(1, 2, Color.RED)

        result = Protocol.encode_board(board, Color.BLUE)

        self.assertIn("1:2:R", result)

    def test_encode_board_blue_as_b(self):
        """Test that BLUE stones are encoded as 'B'."""
        board = HexBoard(5)
        board.make_move(1, 2, Color.BLUE)

        result = Protocol.encode_board(board, Color.RED)

        self.assertIn("1:2:B", result)

    def test_encode_board_different_sizes(self):
        """Test encoding boards of different sizes."""
        for size in [3, 7, 11, 15, 26]:
            board = HexBoard(size)
            result = Protocol.encode_board(board, Color.RED)
            self.assertTrue(result.startswith(f"{size} "))

    def test_encode_board_returns_string(self):
        """Test that encode_board returns a string."""
        board = HexBoard(5)
        result = Protocol.encode_board(board, Color.RED)
        self.assertIsInstance(result, str)

    def test_encode_board_single_line(self):
        """Test that encoded board is a single line."""
        board = HexBoard(5)
        board.make_move(0, 0, Color.RED)
        board.make_move(1, 1, Color.BLUE)

        result = Protocol.encode_board(board, Color.RED)

        # Should only have one newline at the end
        self.assertEqual(result.count('\n'), 1)
        self.assertTrue(result.endswith('\n'))


class TestDecodeMove(unittest.TestCase):
    """Test move decoding from agent responses."""

    def test_decode_normal_move(self):
        """Test decoding a normal move."""
        result = Protocol.decode_move("5 5")
        self.assertEqual(result, (5, 5))

    def test_decode_move_with_different_coordinates(self):
        """Test decoding various coordinate pairs."""
        test_cases = [
            ("0 0", (0, 0)),
            ("10 20", (10, 20)),
            ("3 7", (3, 7)),
            ("15 15", (15, 15)),
        ]

        for input_str, expected in test_cases:
            with self.subTest(input=input_str):
                result = Protocol.decode_move(input_str)
                self.assertEqual(result, expected)

    def test_decode_swap_move_lowercase(self):
        """Test decoding 'swap' move (lowercase)."""
        result = Protocol.decode_move("swap")
        self.assertEqual(result, "swap")

    def test_decode_swap_move_uppercase(self):
        """Test decoding 'SWAP' move (uppercase)."""
        result = Protocol.decode_move("SWAP")
        self.assertEqual(result, "swap")

    def test_decode_swap_move_mixed_case(self):
        """Test decoding 'Swap' with mixed case."""
        result = Protocol.decode_move("SwAp")
        self.assertEqual(result, "swap")

    def test_decode_move_with_leading_whitespace(self):
        """Test that leading whitespace is handled."""
        result = Protocol.decode_move("  5 5")
        self.assertEqual(result, (5, 5))

    def test_decode_move_with_trailing_whitespace(self):
        """Test that trailing whitespace is handled."""
        result = Protocol.decode_move("5 5  ")
        self.assertEqual(result, (5, 5))

    def test_decode_move_with_extra_whitespace(self):
        """Test that extra whitespace between coordinates is handled."""
        result = Protocol.decode_move("5   5")
        self.assertEqual(result, (5, 5))

    def test_decode_move_with_tabs(self):
        """Test decoding move with tab separators."""
        result = Protocol.decode_move("5\t5")
        self.assertEqual(result, (5, 5))

    def test_decode_empty_string_raises_error(self):
        """Test that empty string raises ProtocolError."""
        with self.assertRaises(ProtocolError) as context:
            Protocol.decode_move("")
        self.assertIn("Empty", str(context.exception))

    def test_decode_whitespace_only_raises_error(self):
        """Test that whitespace-only string raises ProtocolError."""
        with self.assertRaises(ProtocolError) as context:
            Protocol.decode_move("   ")
        self.assertIn("Empty", str(context.exception))

    def test_decode_single_number_raises_error(self):
        """Test that single number raises ProtocolError."""
        with self.assertRaises(ProtocolError) as context:
            Protocol.decode_move("5")
        self.assertIn("Invalid move format", str(context.exception))

    def test_decode_three_numbers_raises_error(self):
        """Test that three numbers raise ProtocolError."""
        with self.assertRaises(ProtocolError) as context:
            Protocol.decode_move("5 5 5")
        self.assertIn("Invalid move format", str(context.exception))

    def test_decode_non_numeric_raises_error(self):
        """Test that non-numeric coordinates raise ProtocolError."""
        with self.assertRaises(ProtocolError) as context:
            Protocol.decode_move("a b")
        self.assertIn("Invalid move coordinates", str(context.exception))
        self.assertIn("integers", str(context.exception))

    def test_decode_partial_numeric_raises_error(self):
        """Test that partially numeric input raises ProtocolError."""
        with self.assertRaises(ProtocolError) as context:
            Protocol.decode_move("5 x")
        self.assertIn("Invalid move coordinates", str(context.exception))

    def test_decode_float_raises_error(self):
        """Test that float coordinates raise ProtocolError."""
        with self.assertRaises(ProtocolError) as context:
            Protocol.decode_move("5.5 3.2")
        self.assertIn("Invalid move coordinates", str(context.exception))

    def test_decode_negative_coordinates(self):
        """Test that negative coordinates are parsed (validation happens elsewhere)."""
        result = Protocol.decode_move("-1 -1")
        self.assertEqual(result, (-1, -1))

    def test_decode_large_coordinates(self):
        """Test decoding large coordinate values."""
        result = Protocol.decode_move("100 200")
        self.assertEqual(result, (100, 200))

    def test_decode_zero_coordinates(self):
        """Test decoding zero coordinates."""
        result = Protocol.decode_move("0 0")
        self.assertEqual(result, (0, 0))

    def test_decode_invalid_text_raises_error(self):
        """Test that invalid text raises ProtocolError."""
        invalid_inputs = [
            "invalid",
            "move 5 5",
            "5,5",
            "5-5",
            "(5, 5)",
        ]

        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                with self.assertRaises(ProtocolError):
                    Protocol.decode_move(invalid_input)


class TestProtocolError(unittest.TestCase):
    """Test ProtocolError exception."""

    def test_protocol_error_is_exception(self):
        """Test that ProtocolError is an Exception."""
        error = ProtocolError("test")
        self.assertIsInstance(error, Exception)

    def test_protocol_error_message(self):
        """Test that ProtocolError stores message."""
        message = "Invalid protocol format"
        error = ProtocolError(message)
        self.assertEqual(str(error), message)

    def test_protocol_error_can_be_raised(self):
        """Test that ProtocolError can be raised and caught."""
        with self.assertRaises(ProtocolError):
            raise ProtocolError("Test error")


class TestProtocolIntegration(unittest.TestCase):
    """Test integration between encoding and decoding."""

    def test_encode_decode_round_trip(self):
        """Test encoding a position that could be decoded."""
        board = HexBoard(5)
        board.make_move(2, 3, Color.RED)

        # Encode board state
        encoded = Protocol.encode_board(board, Color.BLUE)

        # Verify format is parseable
        self.assertIsInstance(encoded, str)
        self.assertTrue(encoded.endswith('\n'))

        # Simulate agent playing at position
        move_response = "1 1"
        decoded_move = Protocol.decode_move(move_response)

        self.assertEqual(decoded_move, (1, 1))

    def test_protocol_with_actual_game_sequence(self):
        """Test protocol with a realistic game sequence."""
        board = HexBoard(11)

        # Turn 1: RED plays
        move1 = Protocol.decode_move("5 5")
        board.make_move(move1[0], move1[1], Color.RED)

        # Encode state for BLUE
        state_for_blue = Protocol.encode_board(board, Color.BLUE)
        self.assertIn("5:5:R", state_for_blue)

        # Turn 2: BLUE plays
        move2 = Protocol.decode_move("6 6")
        board.make_move(move2[0], move2[1], Color.BLUE)

        # Encode state for RED
        state_for_red = Protocol.encode_board(board, Color.RED)
        self.assertIn("5:5:R", state_for_red)
        self.assertIn("6:6:B", state_for_red)

    def test_protocol_with_swap_move(self):
        """Test protocol handling swap move."""
        board = HexBoard(11)

        # RED plays first
        move1 = Protocol.decode_move("5 5")
        board.make_move(move1[0], move1[1], Color.RED)

        # BLUE receives state and decides to swap
        state_for_blue = Protocol.encode_board(board, Color.BLUE)
        self.assertIn("5:5:R", state_for_blue)

        # BLUE responds with swap
        swap_response = Protocol.decode_move("swap")
        self.assertEqual(swap_response, "swap")

    def test_multiple_moves_ordering(self):
        """Test that multiple moves are all present in encoding."""
        board = HexBoard(5)
        moves = [
            (0, 0, Color.RED),
            (1, 1, Color.BLUE),
            (2, 2, Color.RED),
            (3, 3, Color.BLUE),
        ]

        for row, col, color in moves:
            board.make_move(row, col, color)

        encoded = Protocol.encode_board(board, Color.RED)

        # All moves should be present
        self.assertIn("0:0:R", encoded)
        self.assertIn("1:1:B", encoded)
        self.assertIn("2:2:R", encoded)
        self.assertIn("3:3:B", encoded)


if __name__ == '__main__':
    unittest.main()
