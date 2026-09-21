# UMass Quant Discovery Day — participant instructions

## What you are building and trying to win

Your team writes a Python function that controls one bot on a shared board. On every turn, the function receives the current board and your bot's information, then returns one direction to move or `STAY`. Your job is to write the algorithm that chooses that action.

Collect numbered rewards to earn points. Your objective in a round is to finish with more points than every other team. A unique highest score earns one round win; a tied highest score earns nobody a win. After three scheduled rounds on different boards, the most round wins wins the match. Tied match leaders play extra full rounds until there is a unique winner. Cumulative points do not break a tie.

You are writing an automatic bot, not controlling a character with your keyboard during the match. The server handles turns, movement, obstacles, reward collection, scoring, and opponents. You only decide the action for your next turn.

## What is in this download

- `bot.py`: the only code file supplied and the only file you submit.
- `README.md`: these instructions and the complete input/output reference.

There is no SDK, pathfinding code, game engine, or example algorithm in the kit. The supplied bot always returns `STAY`; it is a valid placeholder and scores zero. You must replace its function body with your own code. No imports or external packages are needed to use the input.

## The function you implement

Keep a regular, top-level function named exactly `get_move`, taking one argument:

```python
def get_move(state):
    return "STAY"
```

The server calls `get_move(state)` once per turn. You do not call it repeatedly yourself during the event, write the game loop, or create the live state. Read the supplied `state` dictionary and **return one action string**. Each call controls just one turn.

| Returned string | Effect from your current `(x, y)` |
| --- | --- |
| `"UP"` | Attempt to move to `(x, y - 1)`. |
| `"DOWN"` | Attempt to move to `(x, y + 1)`. |
| `"LEFT"` | Attempt to move to `(x - 1, y)`. |
| `"RIGHT"` | Attempt to move to `(x + 1, y)`. |
| `"STAY"` | Stay in place. |

Return the string itself, with exactly that capitalization. Do not print your answer, return coordinates, return several moves, or return a changed board. Reaching the end of the function without a return produces `None`, which is invalid. Do not rename the function to `move`, make it `async`, put it inside a class, or wait for keyboard input.

For example, returning `"RIGHT"` when your position is `[2, 3]` requests a move to `[3, 3]`. It does not request any other future moves. If that cell is blocked or outside the board, you stay where you are. The next call tells you where you actually ended up.

## Input: an ordinary Python dictionary

`state` contains these fields on every call to `get_move`:

| Key | Type | Meaning |
| --- | --- | --- |
| `state["board"]` | List of lists | The entire current board; each inner list is one row. |
| `state["position"]` | Two-element list `[x, y]` | Your current column and row. |
| `state["score"]` | Number | Your points in this round; may be fractional. |
| `state["turn"]` | Integer | Current turn number, starting at `0`. |
| `state["total_turns"]` | Integer | Total number of turns in the round. |
| `state["turns_remaining"]` | Integer | Turns left, including the action currently requested. |
| `state["width"]` | Integer | Number of columns. |
| `state["height"]` | Integer | Number of rows. |

Use dictionary access, such as `state["score"]`, not `state.score`. The dictionary contains data only; it has no game-specific methods or movement helpers.

### Reading the 2D board

**Access a cell with `state["board"][y][x]`: row first, then column.** Your position is `[x, y]`, so the order used to index the board is reversed.

| Cell value | Meaning |
| --- | --- |
| `"X"` | Obstacle; you cannot enter this cell. This is an uppercase string. |
| `0` | Empty, traversable cell. This is an integer. |
| `1` through `9` | Traversable cell with a reward worth that many points. These are integers. |

The top-left cell is `(0, 0)`. Increasing x moves right; increasing y moves down. Valid coordinates satisfy `0 <= x < state["width"]` and `0 <= y < state["height"]`. All rows have the same length. The board contains no symbols for bots, including your own; your position is supplied separately. Opponent positions, scores, actions, and identities are not supplied.

This small input illustrates the format; event boards are larger:

```python
state = {
    "board": [
        [0, 5, "X"],
        [0, "X", 2],
        [3, 0, 0],
    ],
    "position": [0, 0],
    "score": 0.0,
    "turn": 0,
    "total_turns": 200,
    "turns_remaining": 200,
    "width": 3,
    "height": 3,
}
```

In this example, `state["board"][0][1]` is the integer `5`, and `state["board"][1][1]` is the string `"X"`. This example explains the representation; it does not prescribe an action.

Each call receives a fresh snapshot. Editing the dictionary or its board does not change the real board, your position, your score, or another team's input. Only the action you return affects the game. Collected reward cells become `0` in subsequent snapshots; obstacles remain `"X"`.

## What happens in a round

1. Everyone starts at `(0, 0)`, an empty, traversable cell, with zero points.
2. Each bot receives the same pre-move board snapshot, together with its own position, score, and turn information.
3. Each bot returns one action before the decision deadline.
4. The server resolves all moves simultaneously and awards collected rewards.
5. The server calls your function again with updated information until the configured turn count is reached.

A move covers at most one cell, with no diagonals. Hitting a wall or board edge leaves you in place without another penalty. Players never block each other: overlapping, swapping positions, and entering the same cell are allowed.

Entering a reward collects it once and removes it permanently. If multiple bots enter the same reward on the same turn, they split its value equally. For example, two bots entering a 9-point reward each receive 4.5 points. Staying in place or revisiting an emptied cell awards nothing. Execution order gives no collection advantage.

Points and bot memory reset each round. Three scheduled rounds use different boards. After those rounds, tied match leaders play another full board; if its highest score also ties, only the tied top scorers continue to the next extra round. Repeat until one wins.

Default settings: 40 columns × 40 rows, 200 turns, 12% obstacles, and rewards on about 23% of eligible cells. Hosts can change settings before creating a lobby; read that lobby's settings. Dimensions may be 10–60 per side and rounds 100–400 turns. The illustrative 3 × 3 input above is only a small function-call example. The engine uses exact scoring internally; displayed scores are rounded to three decimal places.

## Optional initialization and memory

You may define `initialize(state)` in the same file. It is called once before the first turn of each round, with the same fields as above plus `state["bot_seed"]`, an integer. Its return value is ignored. This function is optional; `get_move` is the required entry point.

Python's `random` module is seeded by the runner before your file is loaded. The `bot_seed` field is supplied during initialization only. Module-level variables survive between turns in the same round. A new process starts each round, so memory does not carry between rounds. Changing an input snapshot is not how you update the real game.

## Python environment and limits

The official runtime is Python 3.11. Use that version locally for matching behavior. No external packages are provided. The following standard-library imports are allowed:

```text
collections, heapq, math, random, itertools, functools, statistics,
bisect, array, enum, typing, dataclasses, copy, operator
```

Normal Python built-ins such as lists, dictionaries, `len`, and `range` are available without imports. There is no `game_sdk` module. Do not use other imports, external files, network calls, subprocesses, or attempts to inspect other teams or the host.

Default limits are **100 milliseconds per decision**, **2 seconds for loading your source plus initialization**, and **256 MB memory**. Check the lobby for configured time limits. Your code runs in an isolated container with a one-CPU limit, a 16-process cap, and a read-only root filesystem.

| Situation | Result |
| --- | --- |
| Ordinary exception or invalid returned action | `STAY` for this turn; the bot may continue next turn. |
| Decision timeout, process death, or corrupted response protocol | `STAY` for the rest of this round. |
| Import or initialization failure/timeout | `STAY` throughout this round. |
| Next round begins | A fresh process is started. |

One bot's failure does not stop other teams. Normal `print()` output is discarded on the event server. Validation messages and your team's diagnostics report errors; organizers can access all teams' diagnostics.

## Getting started and checking your function

1. Download and extract this kit.
2. Install Python 3.11 and open `bot.py` in your editor.
3. Implement the body of `get_move(state)` using the input/output contract above.
4. Check your file locally, then upload it to the website for validation.

From a terminal in the extracted folder, check Python syntax:

```sh
python -m py_compile bot.py
```

Use `python3` on macOS/Linux or `py -3.11` on Windows if `python` is unavailable. Successful syntax compilation produces no terminal output; it does not check your bot's behavior.

To try a single call, start Python with `python`, enter `from bot import get_move`, paste the illustrative `state = {...}` dictionary above, and enter `get_move(state)`. The unedited placeholder returns `'STAY'`. If you defined initialization, import and call `initialize(state)` first with a `"bot_seed"` integer added to that sample dictionary. This is a manual input/output check, not a game simulation. Local calls do not enforce event time or import limits.

Running `python bot.py` alone only defines your function and exits. The kit intentionally does not include a local engine, game simulator, or benchmark. Ask the organizers about a full practice match. Do not copy the sample dictionary into your submitted function: the server supplies the real observation on each call.

## Submitting your bot

1. Open the organizers' event link, enter the six-character game code, and join with your team's name.
2. Upload **one UTF-8 file named exactly `bot.py`**, no larger than **100,000 bytes**. Do not upload a ZIP, notebook, README, or folder. Any additional functions you write must be in this same file.
3. Wait for **Bot Valid**. Validation checks syntax, imports, `get_move`, optional initialization, and one small input in the event container. If it fails, read the message, fix the file, and upload again.
4. Click **Mark ready** and keep the team tab available. Uploading a replacement revalidates it and clears ready status; mark ready again afterward.
5. Submit before the organizers' deadline. Once the match starts, submissions are frozen, including between scheduled rounds and tiebreakers.

Validation tests one small input, not every possible board. A valid submission follows the API and limits; it does not need a high score to pass validation. Organizers may override ready flags but cannot start with an invalid bot.

## Frequently asked questions

**What exactly am I expected to write?** The algorithm inside `get_move(state)` that returns one allowed action for the current turn. Your final deliverable is `bot.py`.

**Do I need to parse JSON, print moves, or write the engine?** No. The runner passes an ordinary dictionary. Your function returns an action string. Everything else runs on the server.

**Where are the other bots on my board?** They are not included. Your own position is a separate `[x, y]` list. Bots are never obstacles.

**Can I change the board or my coordinates to move?** No. Changes to input data affect only your local copy. Return a direction to request movement.

**Can I return several actions at once?** No. Return one string per call. The server asks again next turn.

**Why did my bot stay in place?** It may have returned `STAY`, hit a wall or boundary, returned an invalid action, raised an exception, or been retired after a timeout or crash. Check your team's diagnostics.

**Can I upload another file or install packages?** No. Put all submission code in `bot.py` and use only the allowed imports.

**Can I update my submission?** Before match start, upload again and mark ready again. After match start, ask an organizer about any issue; submissions stay frozen for that match.

**Does closing my browser stop the bot?** Computation runs on the server. Keep your team tab to preserve access to its session. If you lose access, ask an organizer rather than creating duplicate teams.

**Can I pause the replay?** Yes. It shows already computed results; playback controls cannot change actions or scores. Use **Follow host** to return to shared playback.

**What are the policies on AI tools, collaboration, eligibility, prizes, and appeals?** Ask the organizers. This document does not set those event-specific policies.

**Where do other questions go?** Ask the organizers, including Ishan. For a technical issue, include the exact error message, Python version, and command or website step you used.
