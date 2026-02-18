#!/usr/bin/env python3
"""
Test script for swap-always agent.

This tests if the game engine correctly handles and terminates
a player that repeatedly makes illegal swap moves.
"""

import sys
from engine.game import GameController
from engine.constants import Color, DEFAULT_BOARD_SIZE
from players.subprocess_player import SubprocessPlayer
from players.terminal_player import TerminalPlayer
from view.terminal_view import TerminalView


def main():
    """Run a test game with the swap-always agent."""

    board_size = 11

    print("="*70)
    print("SWAP-ALWAYS AGENT TEST")
    print("="*70)
    print("\nThis test runs an agent that ALWAYS tries to swap.")
    print("The game should automatically terminate the agent after")
    print("repeated illegal move attempts.\n")
    print("="*70)

    # Create game controller
    game = GameController(board_size=board_size)

    # Create players
    # RED: Random agent (plays normally)
    red_player = SubprocessPlayer(
        color=Color.RED,
        program_path="python3",
        args=["examples/python/random_agent.py"],
        timeout=5.0,
        name="Random Agent (RED)"
    )

    # BLUE: Swap-always agent (always tries to swap)
    blue_player = SubprocessPlayer(
        color=Color.BLUE,
        program_path="python3",
        args=["examples/python/swap_always_agent.py"],
        timeout=5.0,
        name="Swap-Always Agent (BLUE)"
    )

    # Create view
    view = TerminalView(show_player_stats=True)

    # Start game
    if not game.start_game(red_player, blue_player):
        print("Failed to start game")
        return 1

    print("\n" + "="*70)
    print("GAME STARTED")
    print("="*70)

    # Game loop
    turn_count = 0
    max_turns = 100  # Safety limit

    while turn_count < max_turns:
        turn_count += 1

        # Display board state
        view.render_game_state(game)

        # Play one turn
        continue_game = game.play_turn()

        if not continue_game:
            # Game ended
            break

    # Display final results
    print("\n" + "="*70)
    print("GAME ENDED")
    print("="*70)

    view.render_game_state(game)
    view.render_game_result(game)

    # Show game summary
    summary = game.get_game_summary()
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"Status: {summary['status']}")
    print(f"Winner: {summary['winner']}")
    print(f"Total Turns: {summary['total_turns']}")
    print(f"RED Errors: {summary['red_errors']}")
    print(f"BLUE Errors: {summary['blue_errors']}")

    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)

    if summary['blue_errors'] >= 3:
        print("✓ PASS: Swap-always agent accumulated errors as expected")
        print(
            f"  The agent made {summary['blue_errors']} errors before being terminated")
    else:
        print("✗ FAIL: Expected more errors from swap-always agent")

    if summary['status'] == 'error':
        print("✓ PASS: Game terminated with ERROR status (player forfeit)")
    else:
        print(
            f"? NOTICE: Game status is '{summary['status']}' (expected 'error')")

    if summary['winner'] == 'RED':
        print("✓ PASS: RED won (opponent forfeited)")
    else:
        print(f"? NOTICE: Winner is {summary['winner']} (expected RED)")

    print("\n" + "="*70)

    # Cleanup
    red_player.cleanup()
    blue_player.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
