"""
Unit tests for MinimaxPlayer and supporting utilities.
"""

import unittest

from engine.board import HexBoard
from engine.constants import Color
from players.minimax_player import MinimaxPlayer, dijkstra_shortest_path, _apply_move


class TestDijkstraShortestPath(unittest.TestCase):

    def test_empty_board_red(self):
        board = HexBoard(3)
        # On empty 3x3 board RED needs at least 3 stones (one per row) to connect top-bottom
        dist = dijkstra_shortest_path(board, Color.RED)
        self.assertEqual(dist, 3)

    def test_empty_board_blue(self):
        board = HexBoard(3)
        dist = dijkstra_shortest_path(board, Color.BLUE)
        self.assertEqual(dist, 3)

    def test_red_already_won(self):
        board = HexBoard(3)
        for row in range(3):
            board.make_move(row, 0, Color.RED)
        dist = dijkstra_shortest_path(board, Color.RED)
        self.assertEqual(dist, 0)

    def test_blue_already_won(self):
        board = HexBoard(3)
        for col in range(3):
            board.make_move(0, col, Color.BLUE)
        dist = dijkstra_shortest_path(board, Color.BLUE)
        self.assertEqual(dist, 0)

    def test_opponent_blocks_path(self):
        # Fill all of RED's cells with BLUE stones — RED has no path
        board = HexBoard(3)
        for row in range(3):
            for col in range(3):
                board.make_move(row, col, Color.BLUE)
        dist = dijkstra_shortest_path(board, Color.RED)
        self.assertEqual(dist, float("inf"))

    def test_partial_own_stones_reduce_cost(self):
        board = HexBoard(3)
        board.make_move(0, 1, Color.RED)  # top row
        board.make_move(1, 1, Color.RED)  # middle row
        # RED now needs just 1 more stone to reach bottom row
        dist = dijkstra_shortest_path(board, Color.RED)
        self.assertEqual(dist, 1)


class TestApplyMove(unittest.TestCase):

    def test_does_not_mutate_original(self):
        board = HexBoard(4)
        child = _apply_move(board, (2, 2), Color.RED)
        self.assertEqual(board.get_cell(2, 2), Color.EMPTY)
        self.assertEqual(child.get_cell(2, 2), Color.RED)


class TestMinimaxPlayer(unittest.TestCase):

    def _make_player(self, color=Color.RED, depth=2):
        p = MinimaxPlayer(color, depth=depth)
        p.initialize(5)
        return p

    def test_initialize(self):
        p = self._make_player()
        self.assertEqual(p.board_size, 5)

    def test_returns_legal_move(self):
        p = self._make_player()
        board = HexBoard(5)
        move = p.get_move(board)
        self.assertIsNotNone(move)
        row, col = move
        self.assertTrue(board.is_valid_position(row, col))
        self.assertTrue(board.is_empty(row, col))

    def test_takes_immediate_win(self):
        """Minimax must take an immediately winning move when available."""
        # Set up a board where RED can win by playing (2, 0)
        # RED needs a path from row=0 to row=2 on a 3x3 board
        p = MinimaxPlayer(Color.RED, depth=1)
        p.initialize(3)
        board = HexBoard(3)
        board.make_move(0, 0, Color.RED)
        board.make_move(1, 0, Color.RED)
        # Playing (2, 0) connects top to bottom → win
        move = p.get_move(board)
        self.assertEqual(move, (2, 0))

    def test_blocks_opponent_win(self):
        """Depth>=2 agent should block an opponent that is about to win."""
        p = MinimaxPlayer(Color.RED, depth=2)
        p.initialize(3)
        board = HexBoard(3)
        # BLUE has left and middle columns covered, only (0,2) needed to win
        board.make_move(0, 0, Color.BLUE)
        board.make_move(0, 1, Color.BLUE)
        # RED should play at (0, 2) to block
        move = p.get_move(board)
        self.assertEqual(move, (0, 2))

    def test_no_moves_returns_none(self):
        p = self._make_player()
        board = HexBoard(3)
        # Fill board with alternating colors so no empty cells remain
        for row in range(3):
            for col in range(3):
                color = Color.RED if (row + col) % 2 == 0 else Color.BLUE
                board.make_move(row, col, color)
        self.assertIsNone(p.get_move(board))

    def test_move_time_recorded(self):
        p = self._make_player(depth=1)
        board = HexBoard(5)
        p.get_move(board)
        self.assertGreater(p.last_move_time, 0.0)

    def test_full_game_completes(self):
        """Minimax vs Random should always produce a winner on a 5x5 board."""
        from engine.game import GameController
        from players.random_player import RandomPlayer

        minimax = MinimaxPlayer(Color.RED, depth=2)
        random_p = RandomPlayer(Color.BLUE)
        game = GameController(board_size=5)
        game.start_game(minimax, random_p)
        while game.play_turn():
            pass
        summary = game.get_game_summary()
        self.assertIn(summary["winner"], [Color.RED.name, Color.BLUE.name])


if __name__ == "__main__":
    unittest.main()
