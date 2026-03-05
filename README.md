# CS 5800 Hex Game - Student Guide

## Table of Contents
1. [Introduction](#1-introduction)
2. [Game Rules](#2-game-rules)
3. [Project Structure](#3-project-structure)
4. [Quick Start](#4-quick-start)
5. [Communication Protocol](#5-communication-protocol)
6. [Start Developing with Example Agents](#6-start-developing-with-example-agents)
7. [Testing Your Agent](#7-testing-your-agent)
8. [Constraints & Limits](#8-constraints--limits)
9. [Debugging Tips](#9-debugging-tips)
10. [Submission Guidelines](#10-submission-guidelines)

---

## 1. Introduction

### What is Hex?

Hex is a two-player abstract strategy game played on a rhombus-shaped hexagonal grid. The game was independently invented by Piet Hein and John Nash in the 1940s.

In this project, you'll develop an AI agent to play Hex competitively. 

**Key Features:**
- Simple rules, complex strategy
- No possibility of a draw
- Pure strategy (no luck element)
- Deep algorithmic challenges

---

## 2. Game Rules

### Board and Players

- The game is played on an **N×N hexagonal grid** (typically 11×11)
- Two players: **RED** and **BLUE**
- Players alternate turns placing their colored stones on empty cells
- RED always moves first

### Objective

Each player aims to connect their opposite sides of the board:
- **RED** must connect the **top edge** to the **bottom edge**
- **BLUE** must connect the **left edge** to the **right edge**

### Winning Condition

A player wins by creating a continuous chain of their stones connecting their two sides. The chain can wind and twist, but must be unbroken.

**Important:** Hex has a mathematical property that guarantees no draw is possible. One player must eventually win.

### Coordinates and Board Representation

**Important:** Even though Hex is played on a hexagonal grid, the coordinate system uses standard **matrix-style (row, column) indexing**.

The board uses **0-indexed coordinates**:
- Rows are numbered `0` to `N-1` (top to bottom)
- Columns are numbered `0` to `N-1` (left to right)
- Position `(0, 0)` is the top-left corner
- Position `(N-1, N-1)` is the bottom-right corner

**Think of it like a 2D array:** `board[row][col]`

**The "hexagonal" part is in the connectivity, not the coordinates:**
- Each cell at `(row, col)` has up to **6 neighbors** (not 4 or 8 like a square grid)
- The neighbors are at positions:
  - `(row-1, col)` - top
  - `(row-1, col+1)` - top-right
  - `(row, col+1)` - right
  - `(row+1, col)` - bottom
  - `(row+1, col-1)` - bottom-left
  - `(row, col-1)` - left

**Example for a 7×7 board:**
```
       0  1  2  3  4  5  6   <- columns
    0  .  .  .  .  .  .  .
     1  .  .  .  .  .  .  .
      2  .  .  .  B  .  .  .   <- B at (2,3) is row 2, col 3
       3  .  .  .  .  .  .  .
        4  .  .  .  .  .  .  .
         5  .  .  .  .  .  .  .
          6  .  .  .  .  .  .  .
          ^
        rows
```

**The 6 neighbors of B at (2,3):**
- `(1, 3)` - top: row 2-1=1, col 3
- `(1, 4)` - top-right: row 2-1=1, col 3+1=4
- `(2, 4)` - right: row 2, col 3+1=4
- `(3, 3)` - bottom: row 2+1=3, col 3
- `(3, 2)` - bottom-left: row 2+1=3, col 3-1=2
- `(2, 2)` - left: row 2, col 3-1=2



### Valid Moves

On your turn, you must place a stone on any **empty cell** by specifying its row and column.

**Invalid moves result in automatic forfeiture:**
- Placing a stone on an occupied cell
- Placing a stone out of bounds
- Improperly formatted output
- Exceeding time or memory limits

### The Swap Rule

To balance the first-player advantage, Hex includes an optional **swap rule**:

- **Only the second player (BLUE)** may invoke the swap rule, and only on their first turn (turn 2 of the game).
- Instead of placing a new stone, BLUE outputs `swap`.
- **What happens:** RED's existing stone at position `(r, c)` is removed, and a BLUE stone is placed at the mirrored position `(c, r)` (row and column are transposed).
- **Colors do not change.** Each player keeps their original color. After the swap, it is RED's turn to move.

**Why mirror?** 

The Hex board has a diagonal symmetry. A strong opening move for RED at `(r, c)` corresponds to an equally strong position for BLUE at `(c, r)`. The swap rule exploits this symmetry — if RED's first move is too strong, BLUE can claim its mirror and force RED to play a different strategy.

**Example:**
```
Turn 1: RED plays (3, 4)
Turn 2: BLUE outputs "swap"
Result: Now instead a RED stone at (3, 4), there is a BLUE stone at (4, 3), and the next turn is RED.
```

---

## 3. Project Structure

The framework is organized as follows:

```
5800_final_proj/
├── engine/                  # Core game logic (DO NOT MODIFY)
│   ├── board.py            # Hex board implementation
│   ├── game.py             # Game controller and flow
│   ├── protocol.py         # Communication protocol
│   └── constants.py        # Game constants
│
├── players/                 # Player implementations (DO NOT MODIFY)
│   ├── base.py             # Abstract player class
│   ├── subprocess_player.py # Subprocess communication
│   ├── gui_player.py       # Human player (GUI)
│   └── terminal_player.py  # Human player (terminal)
│
├── view/                    # Display implementations (DO NOT MODIFY)
│   ├── tkinter_view.py     # GUI interface
│   └── terminal_view.py    # Terminal interface
│
├── examples/                # Sample agents (YOUR STARTING POINT)
│   ├── python/
│   │   └── random_agent.py
│   ├── c/
│   │   └── random_agent.c
│   ├── cpp/
│   │   └── random_agent.cpp
│   └── java/
│       └── RandomAgent.java
│
├── tests/                   # Unit tests (optional reference)
│
├── gui_main.py             # GUI mode launcher
└── terminal_main.py        # Terminal mode launcher
```

### Where Your Code Lives

**Your agent is completely independent:**
- Your code runs as a **separate subprocess**
- Communicates with the framework via **stdin/stdout**
- You can write in Python, C, C++, or Java
- The framework manages game logic, display, and opponent communication
- You only need to implement: **read board state → output move**

---

## 4. Quick Start

### System Requirements

**This framework is designed for and only supports Linux systems.** All instructions assume you are running on a Linux environment (Ubuntu, Debian, or similar distributions).

### Prerequisites

1. **Python 3.x** (for running the framework)
   ```bash
   python3 --version
   ```

2. **tkinter** (for GUI):
   ```bash
   sudo apt-get install python3-tk
   ```

3. **Language-specific tools** (based on your choice):
   - **C**: `gcc` compiler
   - **C++**: `g++` compiler
   - **Java**: JDK 8 or higher
   - **Python**: Already installed (Python 3.x)

### Download the Framework

```bash
# Clone or download the project
cd 5800_final_proj
```

### Test the Framework

Run a test game to ensure everything works:

```bash
# GUI mode: Watch two random agents play against each other
python3 gui_main.py --red-subprocess "python3 examples/python/random_agent.py" --blue-subprocess "python3 examples/python/random_agent.py"
```

You should see a GUI window with a hex board and the game playing automatically.

---

## 5. Communication Protocol

You can implement your agent in any of these languages: python3, c, c++, java. To support different languages, your agent communicates with the game framework through **stdin** and **stdout**. The protocol is simple: one line in, one line out.

### Input Format (What Your Agent Receives)

Each turn, your agent receives a **single line** describing the current board state:

```
<SIZE> <YOUR_COLOR> <MOVES>
```

**Fields:**
1. `<SIZE>`: Board size (integer, e.g., `11`)
2. `<YOUR_COLOR>`: Your color - either `RED` or `BLUE`
3. `<MOVES>`: Comma-separated list of existing moves (format: `row:col:color`)

**Examples:**

```
11 RED 
```
*Empty board, you are RED, it's your first move*

```
11 BLUE 5:5:R
```
*11×11 board, you are BLUE, RED has played at (5,5)*

```
11 RED 5:5:B,6:6:R,7:7:B
```
*You are RED, three moves have been played*

```
19 BLUE 9:9:R,10:10:B,8:9:R
```
*19×19 board, you are BLUE, three moves on the board*

### Output Format (What Your Agent Must Send)

Your agent must output a **single line** with your move:

```
<ROW> <COL>
```

or

```
swap
```

**Examples:**

```
5 7
```
*Place your stone at row 5, column 7*

```
10 3
```
*Place your stone at row 10, column 3*

```
swap
```
*Invoke the swap rule (BLUE's first turn only)*

### Critical Implementation Details

#### 1. Flush stdout After Every Output

**This is essential!** The framework reads from your stdout line by line. If you don't flush, your move will be buffered and never sent.

**Python:**
```python
print(f"{row} {col}")
sys.stdout.flush()  # REQUIRED!
```

**C:**
```c
printf("%d %d\n", row, col);
fflush(stdout);  // REQUIRED!
```

**C++:**
```cpp
std::cout << row << " " << col << std::endl;  // endl flushes automatically
// or
std::cout << row << " " << col << "\n";
std::cout.flush();  // REQUIRED if using \n
```

**Java:**
```java
System.out.println(row + " " + col);
System.out.flush();  // REQUIRED!
```

#### 2. Use a Loop to Handle Multiple Moves

Your agent will receive multiple turns in one game. Use a loop:

```python
while True:
    line = input()
    # Parse and make move
    print(f"{row} {col}")
    sys.stdout.flush()
```

#### 3. Parsing the Input

See the example agents for complete parsing code. Basic approach:

```python
parts = line.strip().split(maxsplit=2)
size = int(parts[0])
my_color = parts[1]  # "RED" or "BLUE"

# Parse moves
board = {}
if len(parts) == 3 and parts[2]:
    for move in parts[2].split(','):
        row, col, color = move.split(':')
        board[(int(row), int(col))] = color
```

### Protocol Flow

```
Framework ─────> Your Agent: "11 RED "
Your Agent ─────> Framework: "5 5"

Framework ─────> Your Agent: "11 BLUE 5:5:R"
Your Agent ─────> Framework: "6 6"

Framework ─────> Your Agent: "11 RED 5:5:R,6:6:B"
Your Agent ─────> Framework: "7 7"
```

### Common Protocol Mistakes

❌ **Forgetting to flush stdout** → Timeout  
❌ **Wrong output format** → Invalid move (forfeit)  
❌ **Printing debug info to stdout** → Protocol error (use stderr!)  
❌ **Not handling the loop** → Only plays one move  
❌ **Zero-based vs one-based indexing confusion** → Out of bounds  

---

## 6. Start Developing with Example Agents

The `examples/` directory contains fully functional random agents in all supported languages. These are your **starting point**.

### Python Example (`examples/python/random_agent.py`)

The Python example is heavily commented and easiest to understand:

**Key functions:**

1. **`parse_board(line)`**
   - Takes the input line
   - Returns: `(size, my_color, board_dict)`
   - `board_dict` is a dictionary: `{(row, col): 'R' or 'B'}`

2. **`get_empty_cells(size, board)`**
   - Finds all unoccupied cells
   - Returns: list of `(row, col)` tuples

3. **`choose_move(size, my_color, board)`**
   - **THIS IS WHERE YOUR AI LOGIC GOES**
   - Currently picks a random empty cell
   - Returns: `(row, col)` tuple

4. **`main()`**
   - Main loop that reads input, calls your functions, outputs moves


### C Example (`examples/c/random_agent.c`)

**Key functions:**
- `parseBoard()` - Parses input line into board array
- `getEmptyCells()` - Finds empty positions
- `chooseMove()` - **YOUR AI LOGIC HERE**

**Memory management:** The C example uses fixed-size arrays (MAX_SIZE = 20). For larger boards, adjust this constant.

### C++ Example (`examples/cpp/random_agent.cpp`)

**Key functions:**
- `parseBoard()` - Uses STL containers (map, vector)
- `getEmptyCells()` - Returns vector of positions
- `chooseMove()` - **YOUR AI LOGIC HERE**

### Java Example (`examples/java/RandomAgent.java`)


**Key methods:**
- `parseBoard()` - Returns array with size, color, and HashMap
- `getEmptyCells()` - Returns List of int arrays
- `chooseMove()` - **YOUR AI LOGIC HERE**

---

## 7. Testing Your Agent

### GUI Mode (Recommended)

The GUI provides visual feedback and is the best way to develop and test your agent.

**Basic Command Structure:**

```bash
python3 gui_main.py --red-subprocess "COMMAND" --blue-subprocess "COMMAND" [other flags]
```

- Replace `"COMMAND"` with your agent's execution command (e.g., `"python3 my_agent.py"`)
- Use `--red-subprocess` to make RED player a subprocess agent
- Use `--blue-subprocess` to make BLUE player a subprocess agent
- If a subprocess flag is not provided, that player will be **human** (interact with the GUI by clicking)
- Add other flags like `--board-size`, `--timeout`, `--memory-limit` as needed (see details below)


**Run Command Examples in Different Languages:**

Before testing your agent, you may need to compile it first depending on the language:

**Note:** Below instructions use random agent in examples folders. All commands run under the project root directory. 

**Python:**
- No compilation needed, run directly:
```bash
python3 gui_main.py --blue-subprocess "python3 ./examples/python/random_agent.py"
```

**C:**
- First compile your agent:
```bash
gcc -o examples/c/random_agent examples/c/random_agent.c
```
- Then run:
```bash
python3 gui_main.py --blue-subprocess "./examples/c/random_agent"
```

**C++:**
- First compile your agent:
```bash
g++ -std=c++11 -o examples/cpp/random_agent examples/cpp/random_agent.cpp
```
- Then run:
```bash
python3 gui_main.py --blue-subprocess "./examples/cpp/random_agent"
```

**Java:**
- First compile to create `.class` file:
```bash
javac examples/java/RandomAgent.java
```
- Then run:
```bash
python3 gui_main.py --blue-subprocess "java -cp ./examples/java RandomAgent"
```

**Command-Line Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--board-size N` | Set board size (3-26) | 11 |
| `--timeout SECONDS` | Time limit per move (overrides auto-selection) | Auto (based on board size) |
| `--memory-limit MB` | Memory limit in MB | 64 |
| `--red-subprocess "CMD"` | Command to run RED agent | Human (GUI) |
| `--blue-subprocess "CMD"` | Command to run BLUE agent | Human (GUI) |
| `--red-name "NAME"` | Display name for RED | "Red Player" |
| `--blue-name "NAME"` | Display name for BLUE | "Blue Player" |



### Terminal Mode (Alternative)

Terminal mode provides a text-based interface for testing.

**Usage:**

Commands are similar to GUI mode, but use `terminal_main.py` instead of `gui_main.py`:

```bash
python3 terminal_main.py \
    --blue-subprocess "python3 examples/python/random_agent.py"
```

All flags (`--board-size`, `--timeout`, `--memory-limit`, `--red-subprocess`, `--blue-subprocess`, etc.) work the same as in GUI mode. Compilation steps for C, C++, and Java are identical.

**Additional Terminal-Specific Flags:**

| Option | Description |
|--------|-------------|
| `--no-stats` | Hide player statistics during game |
| `--show-full-log` | Show complete event log at end of game |
| `--show-move-history` | Show complete move history at end of game |

---

## 8. Constraints & Limits

The framework automatically applies different time limits based on board size. When you run the game with a specific board size, the appropriate time limit is automatically enforced.

**Automatic Time Limits:**
| Board Size | Time limit |
| --- | --- |
11×11 | 150 ms
15×15 | 200 ms
19×19 | 250 ms
21×21 | 300 ms

**Note:** For board sizes not listed above, the framework uses a default timeout of 1.0 second.

**Memory Limit:**
All sizes: 64 MB (configurable with `--memory-limit` flag)

**How to use:**

Simply specify the board size and the time limit will be applied automatically:
```bash
# Automatically uses 150ms timeout for 11x11 board
python3 gui_main.py --board-size 11 --red-subprocess "python3 my_agent.py"

# Automatically uses 250ms timeout for 19x19 board  
python3 gui_main.py --board-size 19 --red-subprocess "python3 my_agent.py"

# Override with custom timeout if needed (e.g., for testing)
python3 gui_main.py --board-size 11 --timeout 2.0 --red-subprocess "python3 my_agent.py"
```

**Testing your agent:** Make sure your algorithm can work efficiently under different board sizes and their corresponding time/memory constraints.

---

## 9. Debugging Tips

### Using stderr for Debug Output

**Never print to stdout except for your move!** Stdout is for protocol communication only.

Use **stderr** for all debug output:

**Python:**
```python
import sys
print(f"DEBUG: Evaluating position {pos}", file=sys.stderr)
sys.stderr.flush()
```

**C:**
```c
fprintf(stderr, "DEBUG: Evaluating position (%d, %d)\n", row, col);
fflush(stderr);
```

**C++:**
```cpp
std::cerr << "DEBUG: Evaluating position " << row << "," << col << std::endl;
```

**Java:**
```java
System.err.println("DEBUG: Evaluating position " + row + "," + col);
System.err.flush();
```

**Where to see your debug output:**

- **GUI Mode**: Your stderr output appears in real-time in the **Event Log** panel in the GUI window. Look for messages prefixed with `[Your Agent Name]`.

- **Terminal Mode**: Your stderr output appears in the terminal console mixed with game events as the game progresses.

The framework automatically captures and displays stderr output without interfering with the stdin/stdout protocol communication.

**Example:**
If your agent prints `fprintf(stderr, "Considering move (3,4)\n");`, you'll see:
```
[INFO] [14:23:15] [Subprocess (my_agent.py)] Considering move (3,4)
```
in the Event Log.

---

## 10. Submission Guidelines

### What to Submit

Submit your agent as a **single source code file**:
- Python: `my_agent.py` (or any `.py` filename)
- C: `my_agent.c` (or any `.c` filename)
- C++: `my_agent.cpp` (or any `.cpp` filename)
- Java: `MyAgent.java` (or any `.java` filename with matching class name)

**Filename:** You may use any filename you like. There is no enforced naming convention.

### Include Compilation/Execution Instructions

If using C, C++, or Java, include a brief comment at the top of your file with compilation and usage instructions:

**C:**
```c
// Compile: gcc -o my_agent my_agent.c
// Usage: python3 gui_main.py --red-subprocess "./my_agent"
```

**C++:**
```cpp
// Compile: g++ -std=c++11 -o my_agent my_agent.cpp
// Usage: python3 gui_main.py --red-subprocess "./my_agent"
```

**Java:**
```java
// Compile: javac MyAgent.java
// Usage: python3 gui_main.py --red-subprocess "java MyAgent"
```

