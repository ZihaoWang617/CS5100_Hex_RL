#!/usr/bin/env python3
"""
Main entry point for Hex game.

Usage:
    python main.py                    # Two terminal players (interactive)
    python main.py --board-size 7     # Custom board size
    python main.py --help             # Show help
"""

import sys
import argparse
from typing import Optional
from engine.game import GameController
from engine.constants import Color, DEFAULT_BOARD_SIZE
from players.terminal_player import TerminalPlayer
from players.subprocess_player import SubprocessPlayer
from view.terminal_view import TerminalView


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Hex Game - Terminal Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                          # Two human players
  python main.py --board-size 7                           # Smaller board
  python main.py --red-subprocess "python3 agent.py"      # Human vs AI
  python main.py --blue-subprocess "java Agent"           # Human vs Java AI
  python main.py --red-subprocess "python3 agent1.py" --blue-subprocess "python3 agent2.py"  # AI vs AI
  python main.py --no-stats                               # Hide player stats
  python main.py --show-full-log                          # Show complete log at end
        """
    )

    parser.add_argument(
        '--board-size',
        type=int,
        default=DEFAULT_BOARD_SIZE,
        metavar='N',
        help=f'Board size (default: {DEFAULT_BOARD_SIZE})'
    )

    parser.add_argument(
        '--red-name',
        type=str,
        default='Red Player',
        metavar='NAME',
        help='Name for RED player (default: Red Player)'
    )

    parser.add_argument(
        '--blue-name',
        type=str,
        default='Blue Player',
        metavar='NAME',
        help='Name for BLUE player (default: Blue Player)'
    )

    parser.add_argument(
        '--red-subprocess',
        type=str,
        metavar='COMMAND',
        help='Make RED player a subprocess (e.g., "python3 agent.py" or "java Agent")'
    )

    parser.add_argument(
        '--blue-subprocess',
        type=str,
        metavar='COMMAND',
        help='Make BLUE player a subprocess (e.g., "python3 agent.py" or "java Agent")'
    )

    parser.add_argument(
        '--timeout',
        type=float,
        default=5.0,
        metavar='SECONDS',
        help='Timeout for subprocess players in seconds (default: 5.0)'
    )

    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='Hide player statistics during game'
    )

    parser.add_argument(
        '--show-full-log',
        action='store_true',
        help='Show complete event log at end of game'
    )

    parser.add_argument(
        '--show-move-history',
        action='store_true',
        help='Show complete move history at end of game'
    )

    return parser.parse_args()


def create_player(color: Color, name: str, subprocess_cmd: Optional[str], timeout: float):
    """
    Create a player (either Terminal or Subprocess).

    Args:
        color: Player color
        name: Player name
        subprocess_cmd: Command to run subprocess (None for terminal player)
        timeout: Timeout for subprocess players

    Returns:
        Player instance
    """
    if subprocess_cmd:
        # Parse command
        parts = subprocess_cmd.split()
        program = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        # Create subprocess player
        player = SubprocessPlayer(
            color=color,
            program_path=program,
            args=args,
            timeout=timeout,
            name=name
        )
        return player
    else:
        # Create terminal player
        return TerminalPlayer(color, name)


def main():
    """Main entry point."""
    args = parse_arguments()

    # Validate board size
    if args.board_size < 3 or args.board_size > 26:
        print("Error: Board size must be between 3 and 26")
        sys.exit(1)

    print("=" * 70)
    print("HEX GAME - Terminal Edition".center(70))
    print("=" * 70)
    print()

    # Create game controller
    game = GameController(board_size=args.board_size)

    # Create players (terminal or subprocess based on arguments)
    red_player = create_player(
        Color.RED,
        args.red_name,
        args.red_subprocess,
        args.timeout
    )
    blue_player = create_player(
        Color.BLUE,
        args.blue_name,
        args.blue_subprocess,
        args.timeout
    )

    # Track if we have subprocess players for cleanup
    subprocess_players = []
    if isinstance(red_player, SubprocessPlayer):
        subprocess_players.append(red_player)
    if isinstance(blue_player, SubprocessPlayer):
        subprocess_players.append(blue_player)

    # Create view
    view = TerminalView(game)
    view.show_stats = not args.no_stats

    # Start game
    view.display_game_start()

    # Initialize subprocess players if any
    if subprocess_players:
        print("Initializing subprocess players...")
        for player in subprocess_players:
            if not player.initialize(args.board_size):
                print(f"\nError: Failed to initialize {player.name}")
                print("Make sure the command is correct and the program exists.")
                # Cleanup already initialized players
                for p in subprocess_players:
                    p.cleanup()
                sys.exit(1)
        print("✓ All subprocess players initialized successfully")
        print()

    if not game.start_game(red_player, blue_player):
        print("\nError: Failed to start game")
        # Cleanup subprocess players
        for player in subprocess_players:
            player.cleanup()
        sys.exit(1)

    print("\nGame initialized successfully!")
    print()

    # Game loop with view updates - wrap in try-finally for cleanup
    try:
        while True:
            # Display current state
            view.display_board()

            if view.show_stats:
                view.display_stats()

            view.display_log(recent_count=5)

            # Play one turn
            view.display_turn_start()

            continue_game = game.play_turn()

            if not continue_game:
                # Game ended
                break

            # Small pause to make it readable
            print()

        # Game ended - show final state
        view.display_game_end()

        # Optional: show detailed logs
        if args.show_full_log:
            print()
            input("Press Enter to view full event log...")
            view.display_full_log()

        if args.show_move_history:
            print()
            input("Press Enter to view move history...")
            view.display_move_history()

    finally:
        # Cleanup subprocess players
        if subprocess_players:
            print("\nCleaning up subprocess players...")
            for player in subprocess_players:
                player.cleanup()
            print("✓ Cleanup complete")

    print("\nThank you for playing!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
