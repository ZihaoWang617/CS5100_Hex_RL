#!/usr/bin/env python3
"""
Swap-always Hex agent - Python example for testing.

This agent ALWAYS tries to swap, even when it's illegal.
Used to test the game engine's error handling and auto-termination.

Your agent receives ONE line:
  <SIZE> <YOUR_COLOR> <MOVES>
  Example: 11 RED 5:5:B,6:6:R

Your agent outputs ONE line:
  <ROW> <COL> or swap
  Example: swap

This agent will always output "swap" to test if the game correctly
handles and terminates players making repeated illegal moves.
"""

import sys


def main():
    """
    Main game loop - always tries to swap.
    """
    # Read from stdin until EOF
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        # Always output swap, regardless of game state
        print("swap")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
