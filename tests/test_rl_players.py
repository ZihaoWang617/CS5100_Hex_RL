"""
Tests for random and approximate Q-learning players.
"""

import os
import tempfile
import unittest

from engine.board import HexBoard
from engine.constants import Color
from players.q_learning_player import ApproximateQLearningPlayer
from players.random_player import RandomPlayer


class TestRandomPlayer(unittest.TestCase):
    def test_random_player_returns_legal_move(self):
        player = RandomPlayer(Color.RED, seed=7)
        player.initialize(5)
        board = HexBoard(5)
        board.make_move(0, 0, Color.BLUE)

        move = player.get_move(board)

        self.assertIsNotNone(move)
        self.assertTrue(board.is_valid_position(*move))
        self.assertTrue(board.is_empty(*move))


class TestApproximateQLearningPlayer(unittest.TestCase):
    def test_extract_features_contains_expected_keys(self):
        player = ApproximateQLearningPlayer(Color.RED, epsilon=0.0)
        player.initialize(5)
        board = HexBoard(5)

        features = player.extract_features(board, (2, 2))

        self.assertIn("bias", features)
        self.assertIn("center_control", features)
        self.assertIn("own_largest_group", features)

    def test_update_changes_weights(self):
        player = ApproximateQLearningPlayer(Color.RED, alpha=0.5, gamma=0.9, epsilon=0.0)
        player.initialize(5)
        board = HexBoard(5)
        move = (2, 2)
        next_board = player._simulate_move(board, move, Color.RED)

        player.update(board, move, next_board, reward=1.0, done=True)

        self.assertTrue(any(value != 0.0 for value in player.weights.values()))

    def test_save_and_load_weights(self):
        player = ApproximateQLearningPlayer(Color.RED, epsilon=0.0)
        player.initialize(5)
        player.weights = {"bias": 1.25, "center_control": -0.5}

        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "weights.json")
            player.save_weights(path)

            loaded = ApproximateQLearningPlayer(Color.BLUE, epsilon=0.0)
            loaded.load_weights(path)

        self.assertEqual(player.weights, loaded.weights)
