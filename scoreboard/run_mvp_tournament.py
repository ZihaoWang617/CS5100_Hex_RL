#!/usr/bin/env python3
"""
Run a full double round-robin tournament for MVP submissions and export results
to an Excel workbook.

Usage:
    python run_mvp_tournament.py student_submissions/mvp_submissions/submissions.csv
    python run_mvp_tournament.py student_submissions/mvp_submissions/submissions.csv --board-size 11

The script assumes agent sources live under an agents/ folder next to the CSV.
It compiles or prepares each submission once, runs every pair twice with colors
swapped, and writes summary, match, and raw log sheets into an .xlsx file.
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
import shlex
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = next(
    (
        candidate
        for candidate in (SCRIPT_DIR, *SCRIPT_DIR.parents)
        if (candidate / "engine").is_dir() and (candidate / "players").is_dir()
    ),
    SCRIPT_DIR,
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.constants import (  # noqa: E402
    Color,
    GameStatus,
    DEFAULT_MEMORY_LIMIT,
    DEFAULT_BOARD_SIZE,
    MIN_BOARD_SIZE,
    MAX_BOARD_SIZE,
    get_timeout_for_board_size,
)
from engine.game import GameController  # noqa: E402
from players.subprocess_player import SubprocessPlayer  # noqa: E402


@dataclass(frozen=True)
class AgentEntry:
    index: int
    group_name: str
    student_name: str
    agent_path: str
    display_name: str
    source_path: Optional[Path]


@dataclass
class PreparedAgent:
    entry: AgentEntry
    language: str
    status: str
    message: str
    build_dir: Optional[Path]
    program_path: Optional[str]
    run_args: List[str]
    command_display: str
    compile_stdout: str = ""
    compile_stderr: str = ""
    main_class: Optional[str] = None

    def is_ready(self) -> bool:
        return self.status == "ready"

    def create_player(
        self,
        color: Color,
        timeout: float,
        memory_limit_mb: Optional[float],
        stderr_callback,
    ) -> SubprocessPlayer:
        if not self.is_ready():
            raise ValueError(f"Agent is not ready: {self.entry.display_name}")

        return SubprocessPlayer(
            color=color,
            program_path=self.program_path or "",
            args=list(self.run_args),
            timeout=timeout,
            memory_limit_mb=memory_limit_mb,
            name=self.entry.display_name,
            stderr_callback=stderr_callback,
        )


@dataclass
class AgentStats:
    entry: AgentEntry
    language: str
    build_status: str
    build_message: str
    red_games: int = 0
    red_wins: int = 0
    red_losses: int = 0
    red_forfeits: int = 0
    red_setup_losses: int = 0
    blue_games: int = 0
    blue_wins: int = 0
    blue_losses: int = 0
    blue_forfeits: int = 0
    blue_setup_losses: int = 0

    @property
    def total_games(self) -> int:
        return self.red_games + self.blue_games

    @property
    def total_wins(self) -> int:
        return self.red_wins + self.blue_wins

    @property
    def total_losses(self) -> int:
        return self.red_losses + self.blue_losses

    @property
    def total_forfeits(self) -> int:
        return self.red_forfeits + self.blue_forfeits

    @property
    def total_setup_losses(self) -> int:
        return self.red_setup_losses + self.blue_setup_losses

    def record_scheduled_game(self, color: Color) -> None:
        if color == Color.RED:
            self.red_games += 1
        else:
            self.blue_games += 1

    def record_win(self, color: Color) -> None:
        if color == Color.RED:
            self.red_wins += 1
        else:
            self.blue_wins += 1

    def record_loss(self, color: Color) -> None:
        if color == Color.RED:
            self.red_losses += 1
        else:
            self.blue_losses += 1

    def record_forfeit(self, color: Color) -> None:
        if color == Color.RED:
            self.red_forfeits += 1
        else:
            self.blue_forfeits += 1

    def record_setup_loss(self, color: Color) -> None:
        if color == Color.RED:
            self.red_setup_losses += 1
        else:
            self.blue_setup_losses += 1


@dataclass
class MatchRecord:
    match_id: int
    pairing_id: int
    red_agent: str
    blue_agent: str
    status: str
    winner: str
    turns: int
    red_result: str
    blue_result: str
    reason: str
    red_setup_status: str
    blue_setup_status: str


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    slug = slug.strip("._-")
    return slug or "agent"


def collapse_text(text: str, limit: int = 240) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def fmt_percent(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00%"
    return f"{(numerator / denominator) * 100:.2f}%"


def iso_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat(timespec="seconds")


def command_to_display(command: Sequence[str]) -> str:
    try:
        return shlex.join(list(command))
    except AttributeError:
        return " ".join(shlex.quote(part) for part in command)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a full Hex tournament for MVP submissions and export to Excel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "csv_path",
        help="Path to submissions.csv. Agents are resolved from the sibling agents/ folder.",
    )
    parser.add_argument(
        "--board-size",
        type=int,
        default=DEFAULT_BOARD_SIZE,
        help=f"Board size for every match (default: {DEFAULT_BOARD_SIZE})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Timeout per move in seconds (default: auto-selected from board size)",
    )
    parser.add_argument(
        "--memory-limit",
        type=float,
        default=DEFAULT_MEMORY_LIMIT,
        help=f"Memory limit per agent in MB (default: {DEFAULT_MEMORY_LIMIT})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output .xlsx path (default: next to submissions.csv)",
    )
    return parser.parse_args()


def load_entries(csv_path: Path) -> List[AgentEntry]:
    entries: List[AgentEntry] = []
    agents_dir = csv_path.parent / "agents"

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for index, row in enumerate(reader, start=1):
            group_name = (row.get("group_name") or "").strip()
            student_name = (row.get("student_name") or "").strip()
            agent_path = (row.get("agent_path") or "").strip()

            display_name = group_name or student_name or f"Agent {index}"
            if group_name and student_name:
                display_name = f"{group_name} | {student_name}"
            elif group_name:
                display_name = group_name
            elif student_name:
                display_name = student_name

            source_path = (
                agents_dir / agent_path).resolve() if agent_path else None
            entries.append(
                AgentEntry(
                    index=index,
                    group_name=group_name,
                    student_name=student_name,
                    agent_path=agent_path,
                    display_name=display_name,
                    source_path=source_path,
                )
            )

    return entries


def parse_java_metadata(source_path: Path) -> Tuple[Optional[str], Optional[str]]:
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    package_match = re.search(
        r"^\s*package\s+([A-Za-z_][\w.]*)\s*;", text, re.MULTILINE)
    class_match = re.search(
        r"^\s*(?:public\s+)?(?:final\s+)?class\s+([A-Za-z_][\w]*)", text, re.MULTILINE)

    package_name = package_match.group(1) if package_match else None
    class_name = class_match.group(1) if class_match else source_path.stem

    if package_name:
        return package_name, f"{package_name}.{class_name}"
    return None, class_name


def run_command(command: Sequence[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def compile_agent(entry: AgentEntry, build_root: Path) -> PreparedAgent:
    if not entry.agent_path:
        return PreparedAgent(
            entry=entry,
            language="missing",
            status="missing_path",
            message="agent_path is empty",
            build_dir=None,
            program_path=None,
            run_args=[],
            command_display="",
        )

    if entry.source_path is None or not entry.source_path.exists():
        return PreparedAgent(
            entry=entry,
            language="missing",
            status="missing_source",
            message=f"source not found: {entry.agent_path}",
            build_dir=None,
            program_path=None,
            run_args=[],
            command_display="",
        )

    source_path = entry.source_path
    suffix = source_path.suffix.lower()

    if suffix == ".py":
        command = [sys.executable, str(source_path)]
        return PreparedAgent(
            entry=entry,
            language="python",
            status="ready",
            message="python script",
            build_dir=None,
            program_path=sys.executable,
            run_args=[str(source_path)],
            command_display=command_to_display(command),
        )

    if suffix == ".java":
        build_dir = build_root / \
            f"java_{entry.index}_{safe_slug(source_path.stem)}"
        build_dir.mkdir(parents=True, exist_ok=True)
        _, class_name = parse_java_metadata(source_path)
        class_name = class_name or source_path.stem
        command = ["javac", "-encoding", "UTF-8",
                   "-d", str(build_dir), str(source_path)]
        result = run_command(command, cwd=source_path.parent)
        if result.returncode != 0:
            return PreparedAgent(
                entry=entry,
                language="java",
                status="compile_failed",
                message=f"javac failed with exit code {result.returncode}",
                build_dir=build_dir,
                program_path=None,
                run_args=[],
                command_display=command_to_display(command),
                compile_stdout=result.stdout,
                compile_stderr=result.stderr,
                main_class=class_name,
            )

        run_command_list = ["java", "-cp", str(build_dir), class_name]
        return PreparedAgent(
            entry=entry,
            language="java",
            status="ready",
            message="java compiled",
            build_dir=build_dir,
            program_path="java",
            run_args=["-cp", str(build_dir), class_name],
            command_display=command_to_display(run_command_list),
            compile_stdout=result.stdout,
            compile_stderr=result.stderr,
            main_class=class_name,
        )

    if suffix in {".c", ".cpp"}:
        compiler = "gcc" if suffix == ".c" else "g++"
        std_flag = "c17" if suffix == ".c" else "c++17"
        build_dir = build_root / \
            f"native_{entry.index}_{safe_slug(source_path.stem)}"
        build_dir.mkdir(parents=True, exist_ok=True)
        exe_name = safe_slug(source_path.stem)
        if os.name == "nt":
            exe_name += ".exe"
        exe_path = build_dir / exe_name
        command = [compiler, "-O2",
                   f"-std={std_flag}", "-o", str(exe_path), str(source_path)]
        result = run_command(command, cwd=source_path.parent)
        if result.returncode != 0:
            return PreparedAgent(
                entry=entry,
                language="c" if suffix == ".c" else "cpp",
                status="compile_failed",
                message=f"{compiler} failed with exit code {result.returncode}",
                build_dir=build_dir,
                program_path=None,
                run_args=[],
                command_display=command_to_display(command),
                compile_stdout=result.stdout,
                compile_stderr=result.stderr,
            )

        return PreparedAgent(
            entry=entry,
            language="c" if suffix == ".c" else "cpp",
            status="ready",
            message="native binary compiled",
            build_dir=build_dir,
            program_path=str(exe_path),
            run_args=[],
            command_display=command_to_display(command),
            compile_stdout=result.stdout,
            compile_stderr=result.stderr,
        )

    if source_path.is_file() and os.access(str(source_path), os.X_OK):
        command = [str(source_path)]
        return PreparedAgent(
            entry=entry,
            language=suffix.lstrip(".") or "executable",
            status="ready",
            message="executable file",
            build_dir=None,
            program_path=str(source_path),
            run_args=[],
            command_display=command_to_display(command),
        )

    return PreparedAgent(
        entry=entry,
        language=suffix.lstrip(".") or "unknown",
        status="unsupported_language",
        message=f"unsupported agent file type: {source_path.suffix or '<no extension>'}",
        build_dir=None,
        program_path=None,
        run_args=[],
        command_display="",
    )


def create_player_handle(
    prepared: PreparedAgent,
    color: Color,
    timeout: float,
    memory_limit_mb: Optional[float],
    board_size: int,
    log_rows: List[Dict[str, str]],
    match_id: int,
) -> Tuple[Optional[SubprocessPlayer], str]:
    if not prepared.is_ready():
        return None, prepared.status

    def stderr_callback(message: str) -> None:
        log_rows.append(
            {
                "kind": "game",
                "match_id": str(match_id),
                "subject": prepared.entry.display_name,
                "level": "stderr",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "message": message,
            }
        )

    player = prepared.create_player(
        color=color,
        timeout=timeout,
        memory_limit_mb=memory_limit_mb,
        stderr_callback=stderr_callback,
    )
    init_result = player.initialize(board_size)
    if not init_result:
        player.cleanup()
        return None, "startup_failed"

    # GameController.start_game will call initialize again, so turn it into a no-op.
    player.initialize = lambda board_size: True  # type: ignore[assignment]
    return player, "ready"


def record_game_events(
    logs: List[Dict[str, str]],
    match_id: int,
    controller: GameController,
    subject: str,
) -> None:
    for event in controller.events:
        logs.append(
            {
                "kind": "game",
                "match_id": str(match_id),
                "subject": subject,
                "level": event.level.value,
                "timestamp": iso_timestamp(event.timestamp),
                "message": event.message,
            }
        )


def add_build_logs(log_rows: List[Dict[str, str]], prepared: PreparedAgent) -> None:
    base_row = {
        "kind": "build",
        "match_id": "",
        "subject": prepared.entry.display_name,
        "level": prepared.status,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "message": prepared.message,
    }
    log_rows.append(base_row)

    for line in prepared.compile_stdout.splitlines():
        log_rows.append(
            {
                "kind": "build",
                "match_id": "",
                "subject": prepared.entry.display_name,
                "level": "stdout",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "message": line,
            }
        )

    for line in prepared.compile_stderr.splitlines():
        log_rows.append(
            {
                "kind": "build",
                "match_id": "",
                "subject": prepared.entry.display_name,
                "level": "stderr",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "message": line,
            }
        )


def play_match(
    match_id: int,
    pairing_id: int,
    red_agent: PreparedAgent,
    blue_agent: PreparedAgent,
    board_size: int,
    timeout: float,
    memory_limit_mb: Optional[float],
    stats: Dict[str, AgentStats],
    logs: List[Dict[str, str]],
) -> MatchRecord:
    red_stats = stats[red_agent.entry.display_name]
    blue_stats = stats[blue_agent.entry.display_name]
    red_stats.record_scheduled_game(Color.RED)
    blue_stats.record_scheduled_game(Color.BLUE)

    def finalize_setup_loss(loser: Color, reason: str) -> MatchRecord:
        winner = Color.BLUE if loser == Color.RED else Color.RED
        loser_stats = red_stats if loser == Color.RED else blue_stats
        winner_stats = blue_stats if loser == Color.RED else red_stats
        loser_stats.record_loss(loser)
        loser_stats.record_setup_loss(loser)
        winner_stats.record_win(winner)
        logs.append(
            {
                "kind": "game",
                "match_id": str(match_id),
                "subject": f"match {match_id}",
                "level": "info",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "message": reason,
            }
        )
        return MatchRecord(
            match_id=match_id,
            pairing_id=pairing_id,
            red_agent=red_agent.entry.display_name,
            blue_agent=blue_agent.entry.display_name,
            status="setup_failure",
            winner=winner.name,
            turns=0,
            red_result="win" if loser == Color.BLUE else "loss",
            blue_result="win" if loser == Color.RED else "loss",
            reason=reason,
            red_setup_status=red_agent.status,
            blue_setup_status=blue_agent.status,
        )

    if not red_agent.is_ready() and not blue_agent.is_ready():
        red_stats.record_loss(Color.RED)
        red_stats.record_setup_loss(Color.RED)
        blue_stats.record_loss(Color.BLUE)
        blue_stats.record_setup_loss(Color.BLUE)
        reason = f"both agents unavailable: {red_agent.status} vs {blue_agent.status}"
        logs.append(
            {
                "kind": "game",
                "match_id": str(match_id),
                "subject": f"match {match_id}",
                "level": "warning",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "message": reason,
            }
        )
        return MatchRecord(
            match_id=match_id,
            pairing_id=pairing_id,
            red_agent=red_agent.entry.display_name,
            blue_agent=blue_agent.entry.display_name,
            status="double_setup_failure",
            winner="",
            turns=0,
            red_result="loss",
            blue_result="loss",
            reason=reason,
            red_setup_status=red_agent.status,
            blue_setup_status=blue_agent.status,
        )

    if not red_agent.is_ready():
        red_stats.record_loss(Color.RED)
        red_stats.record_setup_loss(Color.RED)
        blue_stats.record_win(Color.BLUE)
        reason = f"red agent unavailable: {red_agent.status}"
        logs.append(
            {
                "kind": "game",
                "match_id": str(match_id),
                "subject": f"match {match_id}",
                "level": "warning",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "message": reason,
            }
        )
        return MatchRecord(
            match_id=match_id,
            pairing_id=pairing_id,
            red_agent=red_agent.entry.display_name,
            blue_agent=blue_agent.entry.display_name,
            status="setup_failure",
            winner=Color.BLUE.name,
            turns=0,
            red_result="loss",
            blue_result="win",
            reason=reason,
            red_setup_status=red_agent.status,
            blue_setup_status=blue_agent.status,
        )

    if not blue_agent.is_ready():
        red_stats.record_win(Color.RED)
        blue_stats.record_loss(Color.BLUE)
        blue_stats.record_setup_loss(Color.BLUE)
        reason = f"blue agent unavailable: {blue_agent.status}"
        logs.append(
            {
                "kind": "game",
                "match_id": str(match_id),
                "subject": f"match {match_id}",
                "level": "warning",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "message": reason,
            }
        )
        return MatchRecord(
            match_id=match_id,
            pairing_id=pairing_id,
            red_agent=red_agent.entry.display_name,
            blue_agent=blue_agent.entry.display_name,
            status="setup_failure",
            winner=Color.RED.name,
            turns=0,
            red_result="win",
            blue_result="loss",
            reason=reason,
            red_setup_status=red_agent.status,
            blue_setup_status=blue_agent.status,
        )

    game = GameController(board_size=board_size)
    red_player = None
    blue_player = None
    try:
        red_player, red_init_status = create_player_handle(
            red_agent,
            Color.RED,
            timeout,
            memory_limit_mb,
            board_size,
            logs,
            match_id,
        )
        if red_player is None:
            return finalize_setup_loss(Color.RED, f"red startup failed: {red_agent.entry.display_name}")

        blue_player, blue_init_status = create_player_handle(
            blue_agent,
            Color.BLUE,
            timeout,
            memory_limit_mb,
            board_size,
            logs,
            match_id,
        )
        if blue_player is None:
            if red_player:
                red_player.cleanup()
            return finalize_setup_loss(Color.BLUE, f"blue startup failed: {blue_agent.entry.display_name}")

        if red_init_status != "ready" or blue_init_status != "ready":
            if red_player:
                red_player.cleanup()
            if blue_player:
                blue_player.cleanup()
            red_stats.record_loss(Color.RED)
            red_stats.record_setup_loss(Color.RED)
            blue_stats.record_loss(Color.BLUE)
            blue_stats.record_setup_loss(Color.BLUE)
            reason = "player initialization did not complete"
            return MatchRecord(
                match_id=match_id,
                pairing_id=pairing_id,
                red_agent=red_agent.entry.display_name,
                blue_agent=blue_agent.entry.display_name,
                status="controller_failure",
                winner="",
                turns=0,
                red_result="loss",
                blue_result="loss",
                reason=reason,
                red_setup_status=red_agent.status,
                blue_setup_status=blue_agent.status,
            )

        if not game.start_game(red_player, blue_player):
            if red_player:
                red_player.cleanup()
            if blue_player:
                blue_player.cleanup()
            red_stats.record_loss(Color.RED)
            red_stats.record_setup_loss(Color.RED)
            blue_stats.record_loss(Color.BLUE)
            blue_stats.record_setup_loss(Color.BLUE)
            reason = "game controller failed to start"
            return MatchRecord(
                match_id=match_id,
                pairing_id=pairing_id,
                red_agent=red_agent.entry.display_name,
                blue_agent=blue_agent.entry.display_name,
                status="controller_failure",
                winner="",
                turns=0,
                red_result="loss",
                blue_result="loss",
                reason=reason,
                red_setup_status=red_agent.status,
                blue_setup_status=blue_agent.status,
            )

        while game.status == GameStatus.ONGOING:
            if not game.play_turn():
                break

        record_game_events(logs, match_id, game, f"match {match_id}")

        winner_color = game.winner
        turns = game.current_turn

        if game.status == GameStatus.RED_WIN:
            red_stats.record_win(Color.RED)
            blue_stats.record_loss(Color.BLUE)
            red_result = "win"
            blue_result = "loss"
        elif game.status == GameStatus.BLUE_WIN:
            blue_stats.record_win(Color.BLUE)
            red_stats.record_loss(Color.RED)
            red_result = "loss"
            blue_result = "win"
        elif game.status == GameStatus.ERROR:
            assert winner_color is not None
            loser_color = Color.RED if winner_color == Color.BLUE else Color.BLUE
            winner_stats = red_stats if winner_color == Color.RED else blue_stats
            loser_stats = red_stats if loser_color == Color.RED else blue_stats
            winner_stats.record_win(winner_color)
            loser_stats.record_loss(loser_color)
            loser_stats.record_forfeit(loser_color)
            red_result = "win" if winner_color == Color.RED else "loss"
            blue_result = "win" if winner_color == Color.BLUE else "loss"
        else:
            red_result = "loss"
            blue_result = "loss"

        return MatchRecord(
            match_id=match_id,
            pairing_id=pairing_id,
            red_agent=red_agent.entry.display_name,
            blue_agent=blue_agent.entry.display_name,
            status=game.status.value,
            winner=winner_color.name if winner_color else "",
            turns=turns,
            red_result=red_result,
            blue_result=blue_result,
            reason=collapse_text(
                game.events[-1].message if game.events else ""),
            red_setup_status=red_agent.status,
            blue_setup_status=blue_agent.status,
        )
    finally:
        if red_player is not None:
            red_player.cleanup()
        if blue_player is not None:
            blue_player.cleanup()


def xml_escape_text(value: object) -> str:
    return html.escape(str(value), quote=True)


def column_name(index: int) -> str:
    if index < 1:
        raise ValueError("Excel columns are 1-based")
    letters = []
    while index:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


def build_sheet_xml(rows: List[List[object]]) -> str:
    max_col = max((len(row) for row in rows), default=1)
    max_row = max(len(rows), 1)
    dimension = f"A1:{column_name(max_col)}{max_row}"

    row_xml_parts: List[str] = []
    for row_index, row in enumerate(rows, start=1):
        cell_parts: List[str] = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{column_name(col_index)}{row_index}"
            if value is None:
                continue
            if isinstance(value, bool):
                cell_parts.append(
                    f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                cell_parts.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                text = xml_escape_text(value)
                cell_parts.append(
                    f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'
                )
        row_xml_parts.append(
            f'<row r="{row_index}">{"".join(cell_parts)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<sheetData>{"".join(row_xml_parts)}</sheetData>'
        '</worksheet>'
    )


def make_workbook_xml(sheet_names: Sequence[str]) -> str:
    sheet_entries = []
    for index, sheet_name in enumerate(sheet_names, start=1):
        sheet_entries.append(
            f'<sheet name="{xml_escape_text(sheet_name)}" sheetId="{index}" r:id="rId{index}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(sheet_entries)}</sheets>'
        '</workbook>'
    )


def make_workbook_rels(sheet_count: int) -> str:
    rels = []
    for index in range(1, sheet_count + 1):
        rels.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{sheet_count + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(rels)}'
        '</Relationships>'
    )


def make_root_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )


def make_content_types(sheet_count: int) -> str:
    overrides = [
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    for index in range(1, sheet_count + 1):
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f'{"".join(overrides)}'
        '</Types>'
    )


def make_styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><color theme="1"/><name val="Calibri"/><family val="2"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def make_core_props() -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:creator>GitHub Copilot</dc:creator>'
        '<cp:lastModifiedBy>GitHub Copilot</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        '</cp:coreProperties>'
    )


def make_app_props(sheet_names: Sequence[str]) -> str:
    titles = "".join(
        f"<vt:lpstr>{xml_escape_text(name)}</vt:lpstr>" for name in sheet_names)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        f'<Application>Microsoft Excel</Application><HeadingPairs><vt:vector size="2" baseType="variant">'
        '<vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>'
        f'<vt:variant><vt:i4>{len(sheet_names)}</vt:i4></vt:variant></vt:vector></HeadingPairs>'
        f'<TitlesOfParts><vt:vector size="{len(sheet_names)}" baseType="lpstr">{titles}</vt:vector></TitlesOfParts>'
        '</Properties>'
    )


def write_xlsx(output_path: Path, sheet_map: Sequence[Tuple[str, List[List[object]]]]) -> None:
    sheet_names = [name for name, _ in sheet_map]
    sheet_xmls = [build_sheet_xml(rows) for _, rows in sheet_map]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml",
                         make_content_types(len(sheet_map)))
        archive.writestr("_rels/.rels", make_root_rels())
        archive.writestr("docProps/core.xml", make_core_props())
        archive.writestr("docProps/app.xml", make_app_props(sheet_names))
        archive.writestr("xl/workbook.xml", make_workbook_xml(sheet_names))
        archive.writestr("xl/_rels/workbook.xml.rels",
                         make_workbook_rels(len(sheet_map)))
        archive.writestr("xl/styles.xml", make_styles_xml())
        for index, sheet_xml in enumerate(sheet_xmls, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", sheet_xml)


def build_summary_rows(stats: Dict[str, AgentStats], entries: List[AgentEntry]) -> List[List[object]]:
    rows: List[List[object]] = [[
        "agent",
        "group_name",
        "student_name",
        "agent_path",
        "language",
        "build_status",
        "build_message",
        "red_games",
        "red_wins",
        "red_losses",
        "red_forfeits",
        "red_setup_losses",
        "red_success_rate",
        "blue_games",
        "blue_wins",
        "blue_losses",
        "blue_forfeits",
        "blue_setup_losses",
        "blue_success_rate",
        "total_games",
        "total_wins",
        "total_losses",
        "total_forfeits",
        "total_setup_losses",
        "overall_success_rate",
    ]]

    for entry in entries:
        stat = stats[entry.display_name]
        rows.append([
            entry.display_name,
            entry.group_name,
            entry.student_name,
            entry.agent_path,
            stat.language,
            stat.build_status,
            stat.build_message,
            stat.red_games,
            stat.red_wins,
            stat.red_losses,
            stat.red_forfeits,
            stat.red_setup_losses,
            fmt_percent(stat.red_wins, stat.red_games),
            stat.blue_games,
            stat.blue_wins,
            stat.blue_losses,
            stat.blue_forfeits,
            stat.blue_setup_losses,
            fmt_percent(stat.blue_wins, stat.blue_games),
            stat.total_games,
            stat.total_wins,
            stat.total_losses,
            stat.total_forfeits,
            stat.total_setup_losses,
            fmt_percent(stat.total_wins, stat.total_games),
        ])

    return rows


def build_match_rows(matches: List[MatchRecord]) -> List[List[object]]:
    rows: List[List[object]] = [[
        "match_id",
        "pairing_id",
        "red_agent",
        "blue_agent",
        "status",
        "winner",
        "turns",
        "red_result",
        "blue_result",
        "reason",
        "red_setup_status",
        "blue_setup_status",
    ]]

    for record in matches:
        rows.append([
            record.match_id,
            record.pairing_id,
            record.red_agent,
            record.blue_agent,
            record.status,
            record.winner,
            record.turns,
            record.red_result,
            record.blue_result,
            record.reason,
            record.red_setup_status,
            record.blue_setup_status,
        ])

    return rows


def build_log_rows(logs: List[Dict[str, str]]) -> List[List[object]]:
    rows: List[List[object]] = [["kind", "match_id",
                                 "subject", "level", "timestamp", "message"]]
    for log in logs:
        rows.append([
            log.get("kind", ""),
            log.get("match_id", ""),
            log.get("subject", ""),
            log.get("level", ""),
            log.get("timestamp", ""),
            log.get("message", ""),
        ])
    return rows


def run_tournament(csv_path: Path, board_size: int, timeout: float, memory_limit_mb: Optional[float], output_path: Path) -> None:
    entries = load_entries(csv_path)
    if not entries:
        raise ValueError("No submissions found in CSV")

    stats = {
        entry.display_name: AgentStats(
            entry=entry,
            language="",
            build_status="",
            build_message="",
        )
        for entry in entries
    }

    matches: List[MatchRecord] = []
    logs: List[Dict[str, str]] = []

    with tempfile.TemporaryDirectory(prefix="hex_tournament_build_") as build_temp:
        build_root = Path(build_temp)
        prepared_agents: Dict[str, PreparedAgent] = {}

        for entry in entries:
            prepared = compile_agent(entry, build_root)
            prepared_agents[entry.display_name] = prepared
            stats[entry.display_name].language = prepared.language
            stats[entry.display_name].build_status = prepared.status
            stats[entry.display_name].build_message = prepared.message
            add_build_logs(logs, prepared)

        match_id = 1
        pairing_id = 1
        for left_index in range(len(entries)):
            for right_index in range(left_index + 1, len(entries)):
                left = prepared_agents[entries[left_index].display_name]
                right = prepared_agents[entries[right_index].display_name]

                matches.append(
                    play_match(
                        match_id=match_id,
                        pairing_id=pairing_id,
                        red_agent=left,
                        blue_agent=right,
                        board_size=board_size,
                        timeout=timeout,
                        memory_limit_mb=memory_limit_mb,
                        stats=stats,
                        logs=logs,
                    )
                )
                match_id += 1

                matches.append(
                    play_match(
                        match_id=match_id,
                        pairing_id=pairing_id,
                        red_agent=right,
                        blue_agent=left,
                        board_size=board_size,
                        timeout=timeout,
                        memory_limit_mb=memory_limit_mb,
                        stats=stats,
                        logs=logs,
                    )
                )
                match_id += 1
                pairing_id += 1

    summary_rows = build_summary_rows(stats, entries)
    match_rows = build_match_rows(matches)
    log_rows = build_log_rows(logs)
    sheet_map = [
        ("Summary", summary_rows),
        ("Matches", match_rows),
        ("Logs", log_rows),
    ]
    write_xlsx(output_path, sheet_map)


def main() -> int:
    args = parse_arguments()
    csv_path = Path(args.csv_path).expanduser()
    if not csv_path.exists():
        print(f"Error: CSV not found: {csv_path}", file=sys.stderr)
        return 1

    if args.board_size < MIN_BOARD_SIZE or args.board_size > MAX_BOARD_SIZE:
        print(
            f"Error: board size must be between {MIN_BOARD_SIZE} and {MAX_BOARD_SIZE}",
            file=sys.stderr,
        )
        return 1

    timeout = args.timeout if args.timeout is not None else get_timeout_for_board_size(
        args.board_size)
    output_path = Path(args.output).expanduser(
    ) if args.output else csv_path.parent / "mvp_tournament_results.xlsx"

    run_tournament(
        csv_path=csv_path,
        board_size=args.board_size,
        timeout=timeout,
        memory_limit_mb=args.memory_limit,
        output_path=output_path,
    )

    print(f"Tournament complete. Results written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
