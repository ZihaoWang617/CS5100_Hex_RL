"""
Tkinter-based GUI view for Hex game.

Displays game state graphically with clickable hexagons.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from math import sqrt, cos, sin, pi
from datetime import datetime
from typing import Optional
from engine.board import HexBoard
from engine.game import GameController, GameEvent, LogLevel
from engine.constants import Color
from players.subprocess_player import SubprocessPlayer
from players.gui_player import GUIPlayer


COLOR_MAP = {
    Color.EMPTY: '#F0F0F0',  # Light gray
    Color.RED: '#FF6B6B',    # Red
    Color.BLUE: '#4ECDC4'    # Blue/Cyan
}

HOVER_COLOR_MAP = {
    Color.EMPTY: '#E0E0E0',  # Slightly darker gray
    Color.RED: '#FF8B8B',    # Lighter red
    Color.BLUE: '#6EDED4'    # Lighter blue
}


class HexBoardCanvas:
    """Canvas for drawing and managing the hexagonal board."""

    def __init__(self, canvas, board_size):
        self.canvas = canvas
        self.size = board_size
        self.hex_radius = 25  # Default, will be recalculated dynamically
        self.cells = {}  # (row, col) -> hex_id mapping
        self.cell_coords = {}  # hex_id -> (row, col) reverse mapping

    def calculate_optimal_hex_radius(self):
        """Calculate optimal hex radius based on current canvas size."""
        # Update canvas to get actual dimensions
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Use minimum dimension if canvas is very small
        if canvas_width < 100 or canvas_height < 100:
            canvas_width = 800
            canvas_height = 800

        # Calculate max radius that fits the board
        # Account for hex grid geometry and padding
        # Width needed: size * 1.732 * radius + (size-1) * 0.866 * radius + padding
        # Height needed: size * 1.5 * radius + padding

        padding = 100
        max_radius_width = (canvas_width - padding) / \
            (self.size * 1.732 + (self.size - 1) * 0.866)
        max_radius_height = (canvas_height - padding) / (self.size * 1.5 + 0.5)

        # Use the smaller of the two to ensure board fits
        optimal_radius = min(max_radius_width, max_radius_height)

        # Clamp to reasonable bounds
        self.hex_radius = max(12, min(50, optimal_radius))

    def draw_hexagon(self, center_x, center_y, radius, color, tags=None):
        """Draw a single hexagon."""
        points = []
        for i in range(6):
            angle = pi / 3 * i + pi / 6  # Rotate 30 degrees for flat-top hex
            x = center_x + radius * cos(angle)
            y = center_y + radius * sin(angle)
            points.append((x, y))

        hex_id = self.canvas.create_polygon(
            points,
            fill=color,
            outline='#333333',
            width=2,
            tags=tags or []
        )

        return hex_id

    def calculate_hex_position(self, row, col):
        """Convert (row, col) to pixel coordinates using axial/offset layout."""
        size = self.hex_radius
        # Hexagonal grid with row offset layout
        x = col * size * 1.732 + row * size * 0.866 + 80  # offset from left
        y = row * size * 1.5 + 110  # offset from top
        return x, y

    def draw_board(self, board: HexBoard, click_callback=None):
        """Draw the entire board."""
        # Recalculate hex size based on current canvas dimensions
        self.calculate_optimal_hex_radius()

        self.canvas.delete('all')
        self.cells.clear()
        self.cell_coords.clear()

        # Draw hexagons
        for row in range(self.size):
            for col in range(self.size):
                x, y = self.calculate_hex_position(row, col)
                cell_color = board.get_cell(row, col)
                color = COLOR_MAP[cell_color]

                hex_id = self.draw_hexagon(
                    x, y, self.hex_radius, color, tags=['hex'])
                self.cells[(row, col)] = hex_id
                self.cell_coords[hex_id] = (row, col)

                # Add coordinate label
                text_color = '#666666' if cell_color == Color.EMPTY else '#000000'
                self.canvas.create_text(
                    x, y,
                    text=f"{row},{col}",
                    font=('Arial', 8),
                    fill=text_color,
                    tags=['label']
                )

                # Bind click event
                if click_callback:
                    self.canvas.tag_bind(hex_id, '<Button-1>',
                                         lambda e, r=row, c=col: click_callback(r, c))
                    # Hover effects
                    self.canvas.tag_bind(hex_id, '<Enter>',
                                         lambda e, r=row, c=col: self.on_hover(r, c, board))
                    self.canvas.tag_bind(hex_id, '<Leave>',
                                         lambda e, r=row, c=col: self.on_leave(r, c, board))

        # Draw edge labels
        self.draw_edge_labels()

    def on_hover(self, row, col, board):
        """Handle mouse hover over hex."""
        if board.is_empty(row, col):
            hex_id = self.cells[(row, col)]
            self.canvas.itemconfig(hex_id, fill=HOVER_COLOR_MAP[Color.EMPTY])

    def on_leave(self, row, col, board):
        """Handle mouse leave from hex."""
        if board.is_empty(row, col):
            hex_id = self.cells[(row, col)]
            cell_color = board.get_cell(row, col)
            self.canvas.itemconfig(hex_id, fill=COLOR_MAP[cell_color])

    def update_cell(self, row, col, color):
        """Update a single cell's color."""
        if (row, col) in self.cells:
            hex_id = self.cells[(row, col)]
            self.canvas.itemconfig(hex_id, fill=COLOR_MAP[color])

    def draw_edge_labels(self):
        """Draw edge labels showing game goals outside the board boundaries."""
        # Calculate corner hexagon center positions
        top_left_x, top_left_y = self.calculate_hex_position(0, 0)
        top_right_x, top_right_y = self.calculate_hex_position(
            0, self.size - 1)
        bottom_left_x, bottom_left_y = self.calculate_hex_position(
            self.size - 1, 0)
        bottom_right_x, bottom_right_y = self.calculate_hex_position(
            self.size - 1, self.size - 1)

        # For flat-top hexagons:
        # - Top vertex is at center_y - hex_radius
        # - Bottom vertex is at center_y + hex_radius
        # - Left/right vertices are at center_x ± hex_radius * 0.866

        # Different offsets for RED (top/bottom) and BLUE (left/right)
        # RED only needs to clear hex height, BLUE needs more space for text width
        red_label_offset = 20   # Distance from top/bottom boundary to label
        blue_label_offset = 45  # Distance from left/right boundary to label

        # TOP EDGE - RED (connects top edge to top edge)
        # The topmost point of the board is the top vertex of row 0 hexagons
        top_boundary_y = top_left_y - self.hex_radius
        top_center_x = (top_left_x + top_right_x) / 2
        self.canvas.create_text(
            top_center_x, top_boundary_y - red_label_offset,
            text="RED",
            font=('Arial', 16, 'bold'),
            fill=COLOR_MAP[Color.RED]
        )

        # BOTTOM EDGE - RED (connects bottom edge to bottom edge)
        # The bottommost point is the bottom vertex of row (size-1) hexagons
        bottom_boundary_y = bottom_left_y + self.hex_radius
        bottom_center_x = (bottom_left_x + bottom_right_x) / 2
        self.canvas.create_text(
            bottom_center_x, bottom_boundary_y + red_label_offset,
            text="RED",
            font=('Arial', 16, 'bold'),
            fill=COLOR_MAP[Color.RED]
        )

        # LEFT EDGE - BLUE (connects left edge to left edge)
        # Calculate based on middle row to match where the label is vertically centered
        middle_row = self.size // 2
        middle_left_x, middle_left_y = self.calculate_hex_position(
            middle_row, 0)
        left_boundary_x = middle_left_x - self.hex_radius * 0.866
        left_center_y = (top_left_y + bottom_left_y) / 2
        self.canvas.create_text(
            left_boundary_x - blue_label_offset, left_center_y,
            text="BLUE",
            font=('Arial', 16, 'bold'),
            fill=COLOR_MAP[Color.BLUE]
        )

        # RIGHT EDGE - BLUE (connects right edge to right edge)
        # Calculate based on middle row to match where the label is vertically centered
        middle_right_x, middle_right_y = self.calculate_hex_position(
            middle_row, self.size - 1)
        right_boundary_x = middle_right_x + self.hex_radius * 0.866
        right_center_y = (top_right_y + bottom_right_y) / 2
        self.canvas.create_text(
            right_boundary_x + blue_label_offset, right_center_y,
            text="BLUE",
            font=('Arial', 16, 'bold'),
            fill=COLOR_MAP[Color.BLUE]
        )


class TkinterView:
    """Tkinter-based graphical view for Hex game."""

    def __init__(self, game_controller: GameController):
        """Initialize tkinter view."""
        self.controller = game_controller
        self.root = None
        self.canvas = None
        self.hex_canvas = None
        self.status_label = None
        self.turn_label = None
        self.stats_text = None
        self.log_text = None
        self.swap_button = None

        # Click callback for GUI players
        self.click_callback = None

        self.show_log = True
        self.show_stats = True

    def setup_window(self):
        """Create and configure the main window."""
        self.root = tk.Tk()
        self.root.title("Hex Game")

        # Make window resizable
        self.root.resizable(True, True)

        # Set minimum window size to ensure usability
        self.root.minsize(800, 600)

        # Start window in zoomed (maximized) state for best display
        # This works across different DPI settings and screen sizes
        try:
            self.root.state('zoomed')  # Windows/Linux
        except:
            try:
                # macOS alternative
                self.root.attributes('-zoomed', True)
            except:
                # Fallback: use a large default size
                self.root.geometry("1400x900")

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=1)
        # Row 2 contains the board and should expand
        main_frame.rowconfigure(2, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="HEX GAME",
            font=('Arial', 20, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=10)

        # Status bar
        self.status_label = ttk.Label(
            main_frame,
            text="Game Starting...",
            font=('Arial', 12)
        )
        self.status_label.grid(
            row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))

        # Left side: Board canvas
        canvas_frame = ttk.LabelFrame(main_frame, text="Board", padding="5")
        canvas_frame.grid(row=2, column=0, sticky=(
            tk.W, tk.E, tk.N, tk.S), padx=5)

        # Canvas should expand to fill available space
        self.canvas = tk.Canvas(
            canvas_frame,
            bg='white'
        )
        self.canvas.pack(expand=True, fill=tk.BOTH)

        # Initialize hex canvas
        self.hex_canvas = HexBoardCanvas(
            self.canvas, self.controller.board_size)

        # Bind resize event to redraw board with new size
        self.canvas.bind('<Configure>', lambda e: self._on_canvas_resize())

        # Right side: Info panel
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=2, column=1, sticky=(
            tk.W, tk.E, tk.N, tk.S), padx=5)
        info_frame.rowconfigure(1, weight=1)
        info_frame.rowconfigure(3, weight=2)

        # Turn info
        self.turn_label = ttk.Label(
            info_frame,
            text="Turn: 0",
            font=('Arial', 11, 'bold'),
            width=40  # Fixed width to prevent shifting when text changes
        )
        self.turn_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        # Player stats
        stats_frame = ttk.LabelFrame(
            info_frame, text="Player Stats", padding="5")
        stats_frame.grid(row=1, column=0, sticky=(
            tk.W, tk.E, tk.N, tk.S), pady=5)

        self.stats_text = tk.Text(
            stats_frame,
            height=8,
            width=30,
            font=('Courier', 9),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.stats_text.pack(expand=True, fill=tk.BOTH)

        # Controls
        controls_frame = ttk.LabelFrame(
            info_frame, text="Controls", padding="5")
        controls_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)

        self.swap_button = ttk.Button(
            controls_frame,
            text="Swap Move",
            command=self.on_swap_button,
            state=tk.DISABLED
        )
        self.swap_button.pack(fill=tk.X, pady=2)

        # Event log
        log_frame = ttk.LabelFrame(info_frame, text="Event Log", padding="5")
        log_frame.grid(row=3, column=0, sticky=(
            tk.W, tk.E, tk.N, tk.S), pady=5)

        # Scrollbar for log
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_frame,
            height=10,
            width=30,
            font=('Courier', 8),
            wrap=tk.WORD,
            yscrollcommand=log_scroll.set,
            state=tk.DISABLED
        )
        self.log_text.pack(expand=True, fill=tk.BOTH)
        log_scroll.config(command=self.log_text.yview)

    def set_click_callback(self, callback):
        """Set callback for cell clicks (used by GUI players)."""
        self.click_callback = callback

    def _on_canvas_resize(self):
        """Handle canvas resize - redraw board with new dimensions."""
        # Only redraw if game has started
        if self.controller.board:
            self.display_board()

    def display_game_start(self):
        """Display game start information."""
        if self.status_label:
            red_name = self.controller.red_player.name if self.controller.red_player else "Unknown"
            blue_name = self.controller.blue_player.name if self.controller.blue_player else "Unknown"
            self.status_label.config(
                text=f"[RED] {red_name} vs [BLUE] {blue_name} | Board: {self.controller.board_size}x{self.controller.board_size}"
            )

        self.display_board()
        self.display_stats()
        self.display_log()

    def display_board(self):
        """Display/update the board."""
        if self.hex_canvas:
            self.hex_canvas.draw_board(
                self.controller.board, self.handle_cell_click)
        self.root.update()

    def handle_cell_click(self, row, col):
        """Handle click on a board cell."""
        # Check if game is over
        if self.controller.winner is not None:
            messagebox.showinfo(
                "Game Over", "The game is already over. Please start a new game.")
            return

        # Check if it's a subprocess player's turn
        if self.controller.current_player and isinstance(self.controller.current_player, SubprocessPlayer):
            messagebox.showinfo(
                "Not Your Turn", "Please wait for the subprocess player to make a move.")
            return

        # Check if cell is empty
        if not self.controller.board.is_empty(row, col):
            messagebox.showwarning(
                "Invalid Move", f"Cell ({row}, {col}) is already occupied!")
            return

        # Call the registered callback (from GUI player)
        if self.click_callback:
            self.click_callback(row, col)

    def display_turn_start(self):
        """Update turn information."""
        player = self.controller.current_player
        if player and self.turn_label:
            color_tag = '[RED]' if player.color == Color.RED else '[BLUE]'
            self.turn_label.config(
                text=f"Turn {self.controller.current_turn}: {color_tag} {player.name}'s turn"
            )

        # Update swap button availability
        if self.swap_button:
            move_count = self.controller.board.get_move_count()
            if move_count == 1 and not self.controller.board.swap_used:
                self.swap_button.config(state=tk.NORMAL)
            else:
                self.swap_button.config(state=tk.DISABLED)

        self.root.update()

    def display_move(self, row, col, color):
        """Display a move that was made."""
        if self.hex_canvas:
            self.hex_canvas.update_cell(row, col, color)
        self.root.update()

    def display_log(self, recent_count: int = None):
        """Display log events. If recent_count is None, shows all events."""
        if not self.show_log or not self.log_text:
            return

        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)

        # Show all events if recent_count is None, otherwise show only recent ones
        if recent_count is None:
            recent_events = self.controller.events if self.controller.events else []
        else:
            recent_events = self.controller.events[-recent_count:
                                                   ] if self.controller.events else []

        for event in recent_events:
            timestamp = datetime.fromtimestamp(
                event.timestamp).strftime("%H:%M:%S")
            level_prefix = {
                LogLevel.INFO: "[INFO]",
                LogLevel.WARNING: "[WARN]",
                LogLevel.ERROR: "[ERR]",
                LogLevel.CRITICAL: "[CRIT]"
            }.get(event.level, "[LOG]")

            message = f"{level_prefix} [{timestamp}] {event.message}\n"
            self.log_text.insert(tk.END, message)

        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()

    def display_stats(self):
        """Display player statistics."""
        if not self.show_stats or not self.stats_text:
            return

        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)

        # RED player
        if self.controller.red_player:
            red_errors = self.controller.player_errors[Color.RED]
            red_moves = len([m for m in self.controller.move_history
                             if m.get('color') == 'RED'])

            self.stats_text.insert(tk.END, "[RED PLAYER]\n", 'red')
            self.stats_text.insert(
                tk.END, f"  {self.controller.red_player.name}\n")
            self.stats_text.insert(tk.END, f"  Moves: {red_moves}\n")
            self.stats_text.insert(
                tk.END, f"  Errors: {red_errors}/{GameController.MAX_TOTAL_ERRORS}\n\n")

        # BLUE player
        if self.controller.blue_player:
            blue_errors = self.controller.player_errors[Color.BLUE]
            blue_moves = len([m for m in self.controller.move_history
                              if m.get('color') == 'BLUE'])

            self.stats_text.insert(tk.END, "[BLUE PLAYER]\n", 'blue')
            self.stats_text.insert(
                tk.END, f"  {self.controller.blue_player.name}\n")
            self.stats_text.insert(tk.END, f"  Moves: {blue_moves}\n")
            self.stats_text.insert(
                tk.END, f"  Errors: {blue_errors}/{GameController.MAX_TOTAL_ERRORS}\n")

        self.stats_text.tag_config('red', foreground=COLOR_MAP[Color.RED])
        self.stats_text.tag_config('blue', foreground=COLOR_MAP[Color.BLUE])

        self.stats_text.config(state=tk.DISABLED)
        self.root.update()

    def display_game_end(self):
        """Display game over screen."""
        summary = self.controller.get_game_summary()

        winner_text = ""
        if summary['winner']:
            player_name = summary[summary['winner'].lower() + '_player']
            winner_text = f"{summary['winner']} WINS!\n({player_name})"
        else:
            winner_text = "DRAW"

        result = messagebox.showinfo(
            "Game Over",
            f"{winner_text}\n\n"
            f"Total Turns: {summary['total_turns']}\n"
            f"RED Errors: {summary['red_errors']}\n"
            f"BLUE Errors: {summary['blue_errors']}"
        )

        if self.status_label:
            self.status_label.config(text=f"Game Over: {winner_text}")

    def on_swap_button(self):
        """Handle swap button click."""
        # Check if game is over
        if self.controller.winner is not None:
            messagebox.showinfo(
                "Game Over", "The game is already over. Please start a new game.")
            return

        # Check if it's a subprocess player's turn
        if self.controller.current_player and isinstance(self.controller.current_player, SubprocessPlayer):
            messagebox.showinfo(
                "Not Your Turn", "Please wait for the subprocess player to make a move.")
            return

        if self.click_callback:
            self.click_callback("swap")

    def run(self):
        """Run the tkinter event loop."""
        if self.root:
            self.root.mainloop()
