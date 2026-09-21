"""Small local bot check. Run only your own trusted code; this is not a sandbox."""

import argparse
import ast
import importlib.util
import random
import subprocess
import sys
import time
import traceback
from pathlib import Path

ALLOWED_IMPORTS = {
    "collections",
    "heapq",
    "math",
    "random",
    "itertools",
    "functools",
    "statistics",
    "bisect",
    "array",
    "enum",
    "typing",
    "dataclasses",
    "copy",
    "operator",
}
MOVES = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0), "STAY": (0, 0)}
BOARD = [
    [0, 5, 0, "X", 0, 0, 0, 2, 0, 0],
    [0, "X", 0, "X", 0, 3, 0, "X", 0, 0],
    [0, 0, 0, 0, 0, "X", 0, 0, 0, 4],
    [3, "X", "X", 0, 0, 0, 0, "X", 0, 0],
    [0, 0, 0, 0, 8, 0, 0, 0, 0, 0],
    [0, "X", 0, 0, 0, "X", 0, 0, 6, 0],
    [0, 0, 0, "X", 0, 0, 0, "X", 0, 0],
    [2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, "X", 0, 4, 0, "X", 0, 0, "X", 0],
    [0, 0, 0, 0, 0, 0, 7, 0, 0, 0],
]


def run(bot_path, turns):
    board = [row[:] for row in BOARD]
    position = [0, 0]
    score = 0.0

    def observation(turn):
        return {
            "board": [row[:] for row in board],
            "position": position[:],
            "score": score,
            "turn": turn,
            "total_turns": turns,
            "turns_remaining": turns - turn,
            "width": 10,
            "height": 10,
        }

    started = time.perf_counter()
    source = bot_path.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source, filename=str(bot_path))):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [item.name for item in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            )
            for name in names:
                if name.split(".")[0] not in ALLOWED_IMPORTS or getattr(node, "level", 0):
                    raise ImportError(f"Import not allowed in the event: {name}")
    random.seed(12345)
    spec = importlib.util.spec_from_file_location("bot", bot_path)
    bot = importlib.util.module_from_spec(spec)
    sys.modules["bot"] = bot
    spec.loader.exec_module(bot)
    if not callable(getattr(bot, "get_move", None)):
        raise ValueError("Define get_move(state) in bot.py")
    if hasattr(bot, "initialize"):
        bot.initialize({**observation(0), "bot_seed": 12345})
    init_ms = (time.perf_counter() - started) * 1000
    if init_ms > 2000:
        print(f"WARNING: import + initialization took {init_ms:.1f} ms; event default is 2000 ms.")
    slow, maximum_ms = 0, 0.0
    for turn in range(turns):
        started = time.perf_counter()
        try:
            action = bot.get_move(observation(turn))
        except Exception as exc:
            raise RuntimeError(f"get_move failed on turn {turn}: {exc}") from exc
        elapsed_ms = (time.perf_counter() - started) * 1000
        maximum_ms = max(maximum_ms, elapsed_ms)
        slow += elapsed_ms > 100
        if not isinstance(action, str) or action not in MOVES:
            raise ValueError(f"Turn {turn}: expected UP, DOWN, LEFT, RIGHT, or STAY; got {action!r}")
        dx, dy = MOVES[action]
        x, y = position[0] + dx, position[1] + dy
        if 0 <= x < 10 and 0 <= y < 10 and board[y][x] != "X":
            if [x, y] != position:
                score += board[y][x]
                board[y][x] = 0
            position = [x, y]
        print(f"Turn {turn:02}: {action:5} -> {position}, score {score:g}", flush=True)
    print(f"PASS: {turns} local turns completed with valid actions and no exceptions.")
    print(f"Score: {score:g} | Slowest decision: {maximum_ms:.2f} ms | Decisions over 100 ms: {slow}")
    if slow:
        print("WARNING: some decisions exceeded the event's default 100 ms limit.")
    print("This is a small single-player check; upload validation and event limits still apply.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bot", type=Path, default=Path(__file__).with_name("bot.py"))
    parser.add_argument("--turns", type=int, default=20, help="Local turns, 1-100 (default: 20)")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.turns <= 100:
        parser.error("--turns must be between 1 and 100")
    if args.worker:
        try:
            run(args.bot.resolve(), args.turns)
            return 0
        except BaseException:
            traceback.print_exc()
            print("FAIL: fix the error above and run the check again.", file=sys.stderr)
            return 1
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--bot",
        str(args.bot.resolve()),
        "--turns",
        str(args.turns),
    ]
    try:
        # Whole-run timeout catches an infinite loop; it is not event sandbox isolation.
        return subprocess.run(command, timeout=15, check=False).returncode
    except subprocess.TimeoutExpired:
        print(
            "FAIL: local check exceeded 15 seconds. Check for an infinite loop or very slow code.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("Local check cancelled.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
