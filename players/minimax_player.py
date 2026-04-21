"""
Minimax player with Alpha-Beta pruning for Hex.

Heuristic: Dijkstra shortest-path distance to connect own sides minus opponent's.
Move ordering: center-first to improve pruning efficiency.
"""

import heapq
import math
import time
from typing import List, Optional, Tuple, Union

from engine.board import HexBoard
from engine.constants import Color, HEX_DIRECTIONS
from players.base import Player

Move = Tuple[int, int]
INF = float("inf")


class MinimaxPlayer(Player):
    """
    Minimax search with Alpha-Beta pruning.

    Evaluation: (opponent shortest-path length) - (own shortest-path length).
    A smaller own path and larger opponent path means a better position.
    """

    def __init__(self, color: Color, depth: int = 3, name: str = "Minimax Player"):
        super().__init__(color, name)
        self.depth = depth                  # Search depth; higher = stronger but slower
        self.board_size: Optional[int] = None
        self.last_move_time: float = 0.0    # Elapsed time for the last move, used by experiment scripts

    def initialize(self, board_size: int) -> bool:
        self.board_size = board_size
        return True

    def get_move(self, board: HexBoard) -> Union[Move, str, None]:
        legal_moves = board.get_empty_cells()
        if not legal_moves:
            return None

        t0 = time.time()
        move = self._search(board, legal_moves)
        self.last_move_time = time.time() - t0
        return move

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search(self, board: HexBoard, legal_moves: List[Move]) -> Move:
        """Root-level search: try every legal move and return the one with the highest score."""
        best_score = -INF
        best_move = legal_moves[0]
        alpha = -INF   # Lower bound on the score the MAX player can guarantee on this path
        beta = INF     # Upper bound on the score the MIN player can guarantee on this path

        for move in self._order_moves(legal_moves, board.size):
            child = _apply_move(board, move, self.color)
            # Immediate win — no need to search further
            if child.check_win(self.color):
                return move
            # Opponent's turn starts the recursive search at depth-1
            score = self._minimax(child, self.depth - 1, alpha, beta, maximizing=False)
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)

        return best_move

    def _minimax(self, board: HexBoard, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
        """
        Recursive Minimax with Alpha-Beta pruning.

        maximizing=True  -> current turn is ours (MAX node), seek highest value
        maximizing=False -> current turn is opponent's (MIN node), seek lowest value

        Pruning: when alpha >= beta, the parent node will never choose this subtree,
        so we stop expanding it immediately.
        """
        opponent = self.color.opponent()

        # Terminal check: return extreme values if the game is already decided
        if board.check_win(self.color):
            return INF
        if board.check_win(opponent):
            return -INF

        legal_moves = board.get_empty_cells()
        # Leaf node: depth limit reached or board is full — fall back to heuristic
        if depth == 0 or not legal_moves:
            return self._evaluate(board)

        # Determine which color plays at this node
        current_color = self.color if maximizing else opponent
        ordered = self._order_moves(legal_moves, board.size)

        if maximizing:
            value = -INF
            for move in ordered:
                child = _apply_move(board, move, current_color)
                value = max(value, self._minimax(child, depth - 1, alpha, beta, False))
                alpha = max(alpha, value)
                if alpha >= beta:   # Beta cut-off: MIN ancestor won't allow this branch
                    break
            return value
        else:
            value = INF
            for move in ordered:
                child = _apply_move(board, move, current_color)
                value = min(value, self._minimax(child, depth - 1, alpha, beta, True))
                beta = min(beta, value)
                if alpha >= beta:   # Alpha cut-off: MAX ancestor won't allow this branch
                    break
            return value

    # ------------------------------------------------------------------
    # Heuristic
    # ------------------------------------------------------------------

    def _evaluate(self, board: HexBoard) -> float:
        """
        Heuristic evaluation via Dijkstra shortest-path lengths for both sides.

        Returns (opponent path length) - (own path length).
          Positive -> we are ahead (opponent needs more moves to connect)
          Negative -> opponent is ahead
        """
        own_dist = dijkstra_shortest_path(board, self.color)
        opp_dist = dijkstra_shortest_path(board, self.color.opponent())

        # Path length of 0 means already connected (guard against edge cases)
        if own_dist == 0:
            return INF
        if opp_dist == 0:
            return -INF

        # Both sides are completely blocked — treat as draw
        if opp_dist == INF and own_dist == INF:
            return 0.0
        if opp_dist == INF:
            return INF
        if own_dist == INF:
            return -INF

        return float(opp_dist - own_dist)

    # ------------------------------------------------------------------
    # Move ordering
    # ------------------------------------------------------------------

    @staticmethod
    def _order_moves(moves: List[Move], board_size: int) -> List[Move]:
        """
        Sort moves by Manhattan distance to the board center, ascending.

        Center cells have stronger connectivity in Hex, so searching them first
        produces better alpha/beta bounds early and prunes more branches.
        """
        center = (board_size - 1) / 2.0
        return sorted(moves, key=lambda m: abs(m[0] - center) + abs(m[1] - center))


# ------------------------------------------------------------------
# Helpers (module-level so they can be reused in tests)
# ------------------------------------------------------------------

def dijkstra_shortest_path(board: HexBoard, color: Color) -> float:
    """
    Return the minimum number of empty cells needed for `color` to complete a
    winning connection (i.e., stones still required to bridge the two sides).

    Cost model:
      - Own stone  : 0  (already placed, free to traverse)
      - Empty cell : 1  (must place a stone here)
      - Opponent stone : impassable

    RED connects top row (row 0) to bottom row (row size-1).
    BLUE connects left column (col 0) to right column (col size-1).
    """
    size = board.size
    opponent = color.opponent()

    # Source cells and goal predicate differ by color
    if color == Color.RED:
        starts = [(0, c) for c in range(size)]
        goal_check = lambda r, c: r == size - 1
    else:
        starts = [(r, 0) for r in range(size)]
        goal_check = lambda r, c: c == size - 1

    dist: dict = {}
    heap: list = []   # Min-heap entries: (cost, row, col)

    # Seed the heap with all usable source cells
    for r, c in starts:
        cell_color = board.get_cell(r, c)
        if cell_color == opponent:
            continue   # Blocked by opponent — skip this source
        cost = 0 if cell_color == color else 1
        if (r, c) not in dist or cost < dist[(r, c)]:
            dist[(r, c)] = cost
            heapq.heappush(heap, (cost, r, c))

    # Standard Dijkstra expansion
    while heap:
        d, r, c = heapq.heappop(heap)

        # Lazy deletion: skip stale heap entries
        if d > dist.get((r, c), INF):
            continue

        # Reached the goal side — return shortest path cost
        if goal_check(r, c):
            return float(d)

        # Expand all six hex neighbors
        for dr, dc in HEX_DIRECTIONS:
            nr, nc = r + dr, c + dc
            if not board.is_valid_position(nr, nc):
                continue
            cell_color = board.get_cell(nr, nc)
            if cell_color == opponent:
                continue   # Opponent's stone blocks passage
            step = 0 if cell_color == color else 1
            nd = d + step
            if nd < dist.get((nr, nc), INF):
                dist[(nr, nc)] = nd
                heapq.heappush(heap, (nd, nr, nc))

    return INF   # No path exists — all routes are blocked


def _apply_move(board: HexBoard, move: Move, color: Color) -> HexBoard:
    """Return a new board with `move` applied for `color`, leaving the original unchanged."""
    child = HexBoard(board.size)
    child.board = dict(board.board)
    child.move_history = list(board.move_history)
    child.swap_used = board.swap_used
    child.make_move(move[0], move[1], color)
    return child
