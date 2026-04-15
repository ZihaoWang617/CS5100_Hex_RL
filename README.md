# CS 5100 Final Project: Hex AI - RL vs. Minimax

## 1. Project Overview
This project investigates the effectiveness of two distinct AI paradigms in the game of **Hex**: a classical **Minimax search with Alpha-Beta pruning** and a **Reinforcement Learning (Q-Learning) agent**. 

We leverage a robust Hex game framework (originally built for CS 5800) as our foundation to compare a hand-crafted heuristic approach against a self-evolving learning agent.

### Research Questions
* **Can a Reinforcement Learning agent learn to play Hex competitively through self-play** without a hand-crafted evaluation function?
* **How does a Minimax agent scale** in performance and speed as we vary search depth and board size?
* **Which approach is more robust** when facing time constraints and large state spaces?

---

## 2. Project Scope & Threads

### Thread 1: Minimax with Alpha-Beta Pruning
* **Heuristic:** Implementation of a Dijkstra-based shortest-path evaluation function.
* **Optimizations:** Alpha-Beta pruning and center-first move ordering.
* **Experiments:** Performance analysis across board sizes ($7 \times 7, 9 \times 9, 11 \times 11, 13 \times 13$) and search depths ($2$ to $5$).

### Thread 2: Q-Learning with Function Approximation
* **Algorithm:** Q-Learning with linear function approximation using hand-crafted board features.
* **Training:** The agent learns entirely from wins and losses through self-play.
* **Target:** Focus on $7 \times 7$ boards to analyze convergence and learning curves.

---

## 3. Project Structure
```text
CS5100_Hex_RL/
|- engine/                  # Core game logic (Hex adjacency, Board rules)
|- players/                 # Python players used for experiments
|  |- base.py               # Abstract player class
|  |- random_player.py      # Random baseline
|  `- q_learning_player.py  # Approximate Q-learning agent
|- evaluation/              # Batch match/evaluation scripts
|- tests/                   # Unit tests for engine and players
`- training_loop.py         # RL self-play training environment
```
