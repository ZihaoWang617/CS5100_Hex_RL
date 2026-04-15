# CS 5100 Final Project: Hex AI - RL vs. Minimax

## Overview
This project investigates the effectiveness of two distinct AI paradigms in the game of **Hex**: a classical **Minimax search with Alpha-Beta pruning** and a **Reinforcement Learning (Q-Learning) agent**.

We leverage a robust Hex game framework (originally built for CS 5800) as our foundation to compare a hand-crafted heuristic approach against a self-evolving learning agent.

### Research Questions
* **Can a Reinforcement Learning agent learn to play Hex competitively through self-play** without a hand-crafted evaluation function?
* **How does a Minimax agent scale** in performance and speed as we vary search depth and board size?
* **Which approach is more robust** when facing time constraints and large state spaces?

---

## Setup
Create and activate a virtual environment, then install the project requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The current codebase only requires `pytest` beyond the Python standard library.
If you later want to plot learning curves, install optional tools such as:

```bash
pip install matplotlib pandas
```

## Project Scope & Threads

### Thread 1: Minimax with Alpha-Beta Pruning
* **Heuristic:** Implementation of a Dijkstra-based shortest-path evaluation function.
* **Optimizations:** Alpha-Beta pruning and center-first move ordering.
* **Experiments:** Performance analysis across board sizes ($7 \times 7, 9 \times 9, 11 \times 11, 13 \times 13$) and search depths ($2$ to $5$).

### Thread 2: Q-Learning with Function Approximation
* **Algorithm:** Q-Learning with linear function approximation using hand-crafted board features.
* **Training:** The agent learns entirely from wins and losses through self-play.
* **Target:** Focus on $7 \times 7$ boards to analyze convergence and learning curves.

---

## Current Workflow
The current Python repository is centered on the RL experiment pipeline:

1. `engine/` defines the Hex board, move legality, and win detection.
2. `players/random_player.py` provides the random baseline.
3. `players/q_learning_player.py` implements the approximate Q-learning agent.
4. `training_loop.py` runs self-play training and periodically saves checkpoints.
5. `evaluation/run_matches.py` runs repeated matches for evaluation.

## Common Commands
Run the targeted unit tests:

```bash
python -m unittest tests.test_board tests.test_game tests.test_rl_players
```

Run a small smoke-test training job:

```bash
python training_loop.py --episodes 5 --eval-interval 2 --eval-games 4 --output-dir artifacts/training_smoke
```

Run batch evaluation between two player types:

```bash
python evaluation/run_matches.py --red random --blue random --board-size 7 --games 20
```

Evaluate a trained Q-learning checkpoint against a random baseline:

```bash
python evaluation/run_matches.py \
  --red q \
  --red-weights artifacts/training_smoke/weights_ep_5.json \
  --blue random \
  --board-size 7 \
  --games 20
```

Training outputs are written to the directory passed with `--output-dir`, including:
- `training_metrics.csv`
- `weights_ep_<episode>.json`

## Project Structure
```text
CS5100_Hex_RL/
|- engine/                  # Core game logic (Hex adjacency, Board rules)
|- players/                 # Python players used for experiments
|  |- base.py               # Abstract player class
|  |- random_player.py      # Random baseline
|  `- q_learning_player.py  # Approximate Q-learning agent
|- evaluation/              # Batch match/evaluation scripts
|- tests/                   # Unit tests for engine and players
|- requirements.txt         # Python dependencies
`- training_loop.py         # RL self-play training environment
```
