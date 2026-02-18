#!/usr/bin/env python3
"""
Test script to demonstrate memory monitoring for subprocess players.
"""

from players.subprocess_player import SubprocessPlayer
from engine.constants import Color
from engine.board import HexBoard
import time


def main():
    print("Testing subprocess memory monitoring...")
    print("=" * 60)

    # Test 1: Monitor memory without limit
    print("\n=== Test 1: Memory Monitoring (No Limit) ===")
    test_memory_monitoring()

    # Test 2: Memory limit enforcement
    print("\n\n=== Test 2: Memory Limit Enforcement ===")
    test_memory_limit()


def test_memory_monitoring():
    """Test basic memory monitoring."""
    # Create a subprocess player (Java)
    player = SubprocessPlayer(
        color=Color.BLUE,
        program_path="java",
        args=["-cp", "examples/java", "RandomAgent"],
        timeout=5.0,
        name="Java Agent"
    )

    # Initialize
    print("\nInitializing subprocess...")
    if not player.initialize(11):
        print("Failed to initialize!")
        return

    print("✓ Subprocess started successfully")

    # Create a test board
    board = HexBoard(11)

    # Make a few moves and check memory
    for i in range(5):
        print(f"\n--- Move {i+1} ---")

        # Get move
        move = player.get_move(board)

        if move is None:
            print("Player forfeited!")
            break

        # Get memory stats
        current_mem, peak_mem = player.get_memory_stats()

        print(f"Move: {move}")
        print(f"Current Memory: {current_mem:.2f} MB")
        print(f"Peak Memory: {peak_mem:.2f} MB")

        # Place the move
        board.place(move[0], move[1], Color.BLUE)

        time.sleep(0.1)

    # Final stats
    print("\n" + "=" * 60)
    current_mem, peak_mem = player.get_memory_stats()
    print(f"Final Memory Statistics:")
    print(f"  Current: {current_mem:.2f} MB")
    print(f"  Peak: {peak_mem:.2f} MB")
    print("=" * 60)

    # Cleanup
    player.cleanup()
    print("\n✓ Subprocess cleaned up")


def test_memory_limit():
    """Test memory limit enforcement."""
    # Create a subprocess player with a very low memory limit (should trigger kill)
    # Note: Java processes typically use 30-50+ MB, so 10 MB will be exceeded
    player = SubprocessPlayer(
        color=Color.BLUE,
        program_path="java",
        args=["-cp", "examples/java", "RandomAgent"],
        timeout=5.0,
        memory_limit_mb=10.0,  # Very low limit - will be exceeded
        name="Java Agent (Limited)"
    )

    # Initialize
    print("\nInitializing subprocess with 10 MB memory limit...")
    if not player.initialize(11):
        print("Failed to initialize!")
        return

    print("✓ Subprocess started successfully")

    # Create a test board
    board = HexBoard(11)

    # Try to get a move - should be killed due to memory limit
    print("\nAttempting to get move (should exceed memory limit)...")
    move = player.get_move(board)

    if move is None:
        print("✓ Player was correctly stopped (forfeited)")
        current_mem, peak_mem = player.get_memory_stats()
        print(f"  Memory at termination: {current_mem:.2f} MB")
        print(f"  Peak memory: {peak_mem:.2f} MB")
    else:
        print(f"✗ Player returned move {move} (expected forfeit)")

    # Cleanup
    player.cleanup()
    print("\n✓ Subprocess cleaned up")


if __name__ == "__main__":
    main()
