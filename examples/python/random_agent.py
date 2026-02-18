#!/usr/bin/env python3
"""
Simple random Hex agent - Python example.

SIMPLIFIED VERSION - Just one function!

Your agent receives ONE line:
  <SIZE> <YOUR_COLOR> <MOVES>
  Example: 11 RED 5:5:B,6:6:R

Your agent outputs ONE line:
  <ROW> <COL>
  Example: 7 7

That's it! No need to track state, handle errors, or manage game flow.
"""

import sys
import random
import time


def parse_board(line):
    """
    Parse the board state from one line.

    Args:
        line: Input line in format "SIZE COLOR MOVES"

    Returns:
        Tuple of (size, my_color, board_dict)
        where board_dict is {(row, col): 'R' or 'B'}
    """
    parts = line.strip().split(maxsplit=2)

    size = int(parts[0])
    my_color = parts[1]  # "RED" or "BLUE"

    # Parse existing moves
    board = {}
    if len(parts) == 3 and parts[2]:
        moves_str = parts[2]
        for move in moves_str.split(','):
            row, col, color = move.split(':')
            board[(int(row), int(col))] = color

    return size, my_color, board


def get_empty_cells(size, board):
    """Get all empty cells on the board."""
    empty = []
    for row in range(size):
        for col in range(size):
            if (row, col) not in board:
                empty.append((row, col))
    return empty


def choose_move(size, my_color, board):
    """
    Choose your move. This is where your AI logic goes!

    Args:
        size: Board size
        my_color: Your color ("RED" or "BLUE")
        board: Dictionary of existing moves

    Returns:
        Tuple of (row, col) for your move
    """
    # Simple strategy: pick a random empty cell
    empty_cells = get_empty_cells(size, board)

    if not empty_cells:
        return (0, 0)  # Shouldn't happen

    return random.choice(empty_cells)


def main():
    """Loop version - handles multiple moves."""
    while True:
        try:
            # Read the board state (one line per turn)
            line = input()

            # Parse it
            size, my_color, board = parse_board(line)

            # Choose your move
            row, col = choose_move(size, my_color, board)

            # # test timeout
            # time.sleep(7)

            # Output your move
            print(f"{row} {col}")
            sys.stdout.flush()

        except EOFError:
            # Game ended - controller closed our stdin
            break


if __name__ == "__main__":
    main()
