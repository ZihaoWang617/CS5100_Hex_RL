"""
Subprocess player that communicates with external programs.

Wraps student submissions that run as separate processes.
Communicates via stdin/stdout using the protocol.
"""

import subprocess
import threading
from typing import Optional, Tuple, List, Union
from engine.board import HexBoard
from engine.protocol import Protocol, ProtocolError
from engine.constants import Color
from .base import Player


class SubprocessPlayer(Player):
    """
    Player that communicates with an external subprocess.

    The subprocess receives board state via stdin and sends moves via stdout.
    Uses the Protocol for encoding/decoding messages.

    Features:
    - Timeout support for reads
    - Crash detection
    - Error handling
    - Automatic cleanup
    """

    DEFAULT_TIMEOUT = 5.0  # seconds
    DEFAULT_MEMORY_LIMIT_MB = 512.0  # MB

    def __init__(self,
                 color: Color,
                 program_path: str,
                 args: Optional[List[str]] = None,
                 timeout: float = DEFAULT_TIMEOUT,
                 memory_limit_mb: Optional[float] = None,
                 name: Optional[str] = None):
        """
        Initialize subprocess player.

        Args:
            color: Player color (RED or BLUE)
            program_path: Path to executable (e.g., 'python3', 'java', './agent')
            args: Additional arguments (e.g., ['student_agent.py'] for Python)
            timeout: Timeout in seconds for each move
            memory_limit_mb: Memory limit in MB (None for no limit)
            name: Display name (defaults to program name)
        """
        # Generate name from program
        if name is None:
            if args:
                name = f"Subprocess ({args[-1]})"
            else:
                name = f"Subprocess ({program_path})"

        super().__init__(color, name)

        self.program_path = program_path
        self.args = args or []
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb
        self.process = None

        # Memory monitoring
        self.current_memory_mb = 0.0
        self.peak_memory_mb = 0.0

    def initialize(self, board_size: int) -> bool:
        """
        Start the subprocess.

        Args:
            board_size: Size of the game board

        Returns:
            True if subprocess started successfully
        """
        try:
            # Build command
            command = [self.program_path] + self.args

            # Start subprocess
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            # Check if process started successfully
            if self._is_dead():
                stderr_output = self._get_stderr()
                print(f"Subprocess failed to start: {stderr_output}")
                return False

            return True

        except FileNotFoundError:
            print(f"Program not found: {self.program_path}")
            return False
        except Exception as e:
            print(f"Failed to start subprocess: {e}")
            return False

    def get_move(self, board: HexBoard) -> Union[Tuple[int, int], str, None]:
        """
        Get move from subprocess.

        Args:
            board: Current board state

        Returns:
            (row, col) tuple for normal move, "swap" for swap move, or None if subprocess fails/forfeits
        """
        # Check if process is alive
        if self._is_dead():
            stderr_output = self._get_stderr()
            if stderr_output:
                print(f"Process died. stderr output:\n{stderr_output}")
            return None

        try:
            # Encode board state
            message = Protocol.encode_board(board, self.color)

            # Send to subprocess
            self.process.stdin.write(message)
            self.process.stdin.flush()

            # Check if process died during write
            if self._is_dead():
                stderr_output = self._get_stderr()
                if stderr_output:
                    print(
                        f"Process died after sending input. stderr output:\n{stderr_output}")
                return None

            # Read response with timeout
            response = self._read_line_with_timeout(self.timeout)

            # Update memory statistics
            self._update_memory_stats()

            # Check memory limit
            if self._check_memory_limit():
                return None

            if response is None:
                # Timeout or EOF
                stderr_output = self._get_stderr()
                if stderr_output:
                    print(
                        f"No response from {self.name}. stderr output:\n{stderr_output}")
                return None

            # Parse move
            try:
                move = Protocol.decode_move(response)
                # Can be (row, col) tuple or "swap" string
                return move
            except ProtocolError as e:
                # Invalid format
                print(f"Protocol error from {self.name}: {e}")
                stderr_output = self._get_stderr()
                if stderr_output:
                    print(f"stderr output:\n{stderr_output}")
                return None

        except (IOError, BrokenPipeError, ValueError) as e:
            # Pipe broken - process likely crashed
            stderr_output = self._get_stderr()
            if stderr_output:
                print(
                    f"Pipe error from {self.name}. stderr output:\n{stderr_output}")
            return None
        except Exception as e:
            # Unexpected error
            print(f"Unexpected error from {self.name}: {e}")
            stderr_output = self._get_stderr()
            if stderr_output:
                print(f"stderr output:\n{stderr_output}")
            return None

    def cleanup(self):
        """Clean up subprocess."""
        if self.process:
            try:
                # Try graceful termination
                self.process.terminate()

                # Wait briefly for termination
                try:
                    self.process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    # Force kill if didn't terminate
                    self.process.kill()
                    self.process.wait()

            except Exception:
                # Force kill on any error
                try:
                    self.process.kill()
                except:
                    pass

    def _is_dead(self) -> bool:
        """Check if subprocess has died."""
        if self.process is None:
            return True
        return self.process.poll() is not None

    def _get_memory_mb(self) -> Optional[float]:
        """Get current memory usage in MB from /proc."""
        if self.process is None or self._is_dead():
            return None

        try:
            # Read from /proc/<pid>/status
            with open(f'/proc/{self.process.pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        # VmRSS is in kB, convert to MB
                        kb = int(line.split()[1])
                        return kb / 1024.0
        except (FileNotFoundError, ValueError, PermissionError, IOError):
            # /proc not available or process died
            return None

        return None

    def _update_memory_stats(self):
        """Update current and peak memory usage."""
        mem = self._get_memory_mb()
        if mem is not None:
            self.current_memory_mb = mem
            if mem > self.peak_memory_mb:
                self.peak_memory_mb = mem

    def _check_memory_limit(self) -> bool:
        """Check if memory limit exceeded and kill process if so.

        Returns:
            True if limit exceeded and process was killed, False otherwise
        """
        if self.memory_limit_mb is None:
            return False

        if self.current_memory_mb > self.memory_limit_mb:
            print(
                f"{self.name} exceeded memory limit ({self.current_memory_mb:.2f} MB > {self.memory_limit_mb:.2f} MB), terminating process...")
            try:
                self.process.kill()
                self.process.wait(timeout=1.0)
            except Exception:
                pass
            return True

        return False

    def _read_line_with_timeout(self, timeout: float) -> Optional[str]:
        """
        Read a line from subprocess stdout with timeout.

        If timeout is exceeded, the subprocess is killed to prevent:
        - Resource accumulation
        - Delayed responses polluting next turn
        - Zombie threads

        Args:
            timeout: Timeout in seconds

        Returns:
            Line string or None if timeout/EOF
        """
        result = [None]

        def read_line():
            try:
                line = self.process.stdout.readline()
                result[0] = line if line else None
            except Exception:
                result[0] = None

        # Start reading in a thread
        thread = threading.Thread(target=read_line, daemon=True)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            # Timeout exceeded - kill the subprocess
            print(
                f"{self.name} exceeded timeout ({timeout}s), terminating process...")
            try:
                self.process.kill()
                self.process.wait(timeout=1.0)
            except Exception:
                pass
            return None

        return result[0]

    def _get_stderr(self) -> str:
        """Get accumulated stderr output."""
        if self.process and self.process.stderr:
            try:
                return self.process.stderr.read()
            except:
                return ""
        return ""

    def get_memory_stats(self) -> Tuple[float, float]:
        """
        Get memory statistics for this subprocess.

        Returns:
            Tuple of (current_memory_mb, peak_memory_mb)
        """
        return (self.current_memory_mb, self.peak_memory_mb)

    def __repr__(self) -> str:
        cmd = f"{self.program_path} {' '.join(self.args)}"
        return f"<SubprocessPlayer name={self.name} command='{cmd}' color={self.color.name}>"
