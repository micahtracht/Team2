"""Diagonal exploration with distance-weighted reward clusters.

Only this file is needed by the event runner. All distances used for racing
opponents and choosing moves respect walls.
"""

from collections import deque
from math import sqrt
import random


WINDOW = 8
OPENING_TURNS = 40
DIAGONAL_BAND = 1.0
DETOUR_BAND = 8.0  # Perpendicular distance in cells from the diagonal.
SIGHTING_LIFETIME = 12
_memory = None


def initialize(state):
    global _memory
    x, y = state["position"]
    _memory = {
        "start": (x, y),
        "sign": (1 if x < state["width"] / 2 else -1,
                 1 if y < state["height"] / 2 else -1),
        "previous": None,
        "turn": -1,
        "opponents": {},
        "horizontal_first": random.choice((True, False)),
    }


def _paths(board, starts, directions):
    """Multi-source BFS, with the first action on each shortest path."""
    height, width = len(board), len(board[0])
    distances = [[-1] * width for _ in board]
    actions = [["STAY"] * width for _ in board]
    queue = deque()
    for x, y in starts:
        distances[y][x] = 0
        queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for dx, dy, action in directions:
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height
                    and board[ny][nx] != "X" and distances[ny][nx] < 0):
                distances[ny][nx] = distances[y][x] + 1
                actions[ny][nx] = action if distances[y][x] == 0 else actions[y][x]
                queue.append((nx, ny))
    return distances, actions


def _prefix(values):
    result = [[0.0] * (len(values[0]) + 1)]
    for row in values:
        total = 0.0
        previous = result[-1]
        current = [0.0]
        for x, value in enumerate(row):
            total += value
            current.append(total + previous[x + 1])
        result.append(current)
    return result


def _window_sum(prefix, x, y, width, height):
    return (prefix[y + height][x + width] - prefix[y][x + width]
            - prefix[y + height][x] + prefix[y][x])


def get_move(state):
    """Return one legal action without changing the supplied snapshot.

    The first 40 turns favor forward diagonal progress. Reward detours must
    stay within eight cells of the diagonal and beat its best window 2:1.
    After the opening, the same window rule applies without the forward-only
    constraint, allowing the bot to harvest and revisit promising areas.
    """
    global _memory
    board = state["board"]
    width, height = state["width"], state["height"]
    x, y = state["position"]
    turn = state["turn"]
    if (_memory is None or turn <= _memory["turn"]
            or (_memory["previous"] is not None
                and (len(_memory["previous"]) != height
                     or len(_memory["previous"][0]) != width))):
        initialize(state)
    memory = _memory
    previous = memory["previous"]
    sightings = memory["opponents"]
    # Only consecutive snapshots identify a pickup's location reliably.
    if previous is not None and turn == memory["turn"] + 1:
        for cy, row in enumerate(board):
            for cx, value in enumerate(row):
                old = previous[cy][cx]
                if value == 0 and old != "X" and old > 0 and (cx, cy) != (x, y):
                    sightings[cx, cy] = turn
    memory["opponents"] = sightings = {
        point: seen for point, seen in sightings.items()
        if turn - seen < SIGHTING_LIFETIME
    }
    memory["previous"] = [row[:] for row in board]
    memory["turn"] = turn
    if state["turns_remaining"] <= 0:
        return "STAY"

    sx, sy = memory["sign"]
    ox, oy = memory["start"]
    horizontal = [(sx, 0, "RIGHT" if sx > 0 else "LEFT"),
                  (-sx, 0, "LEFT" if sx > 0 else "RIGHT")]
    vertical = [(0, sy, "DOWN" if sy > 0 else "UP"),
                (0, -sy, "UP" if sy > 0 else "DOWN")]
    balance = sx * (x - ox) - sy * (y - oy)
    horizontal_first = balance < 0 or (balance == 0 and memory["horizontal_first"])
    directions = horizontal + vertical if horizontal_first else vertical + horizontal
    distances, actions = _paths(board, [(x, y)], directions)
    enemy_distances = _paths(board, sightings, directions)[0] if sightings else None
    opening = turn < OPENING_TURNS
    progress = sx * (x - ox) + sy * (y - oy)

    def diagonal_distance(cx, cy):
        return abs(sx * (cx - ox) - sy * (cy - oy)) / sqrt(2)

    weights = [[0.0] * width for _ in board]
    for cy, row in enumerate(board):
        for cx, value in enumerate(row):
            distance = distances[cy][cx]
            if (value == "X" or value <= 0 or distance <= 0
                    or distance > state["turns_remaining"]
                    or (opening and sx * (cx - ox) + sy * (cy - oy) <= progress)):
                continue
            enemy = enemy_distances[cy][cx] if enemy_distances else -1
            if 0 <= enemy < distance:
                continue
            # Square roots favor several moderate rewards over one large one.
            # Nearby available rewards add a bounded cluster-density bonus.
            neighbors = 0
            for ny in range(max(0, cy - 1), min(height, cy + 2)):
                for nx in range(max(0, cx - 1), min(width, cx + 2)):
                    other = board[ny][nx]
                    if ((nx, ny) != (cx, cy) and other != "X" and other > 0
                            and 0 < distances[ny][nx] <= state["turns_remaining"]
                            and (enemy_distances is None or enemy_distances[ny][nx] < 0
                                 or enemy_distances[ny][nx] >= distances[ny][nx])):
                        neighbors += 1
            safety = 1.0 if enemy < 0 else min(1.0, (enemy - distance + 1) / 4.0)
            weights[cy][cx] = sqrt(value) * (1 + neighbors / 8) * safety / (1 + distance / WINDOW)

    prefix = _prefix(weights)
    ww, wh = min(WINDOW, width), min(WINDOW, height)
    diagonal = (0.0, None)
    detour = (0.0, None)
    for wy in range(height - wh + 1):
        for wx in range(width - ww + 1):
            lateral = diagonal_distance(wx + (ww - 1) / 2, wy + (wh - 1) / 2)
            if lateral > DETOUR_BAND:
                continue
            score = _window_sum(prefix, wx, wy, ww, wh)
            if lateral <= DIAGONAL_BAND:
                if score > diagonal[0]:
                    diagonal = (score, (wx, wy))
            elif score > detour[0]:
                detour = (score, (wx, wy))
    chosen = diagonal
    if detour[0] > 0 and detour[0] >= 2 * diagonal[0]:
        chosen = detour

    if chosen[1] is not None:
        wx, wy = chosen[1]
        candidates = [(cx, cy) for cy in range(wy, wy + wh)
                      for cx in range(wx, wx + ww) if weights[cy][cx] > 0
                      and (chosen is detour or not opening
                           or diagonal_distance(cx, cy) <= DIAGONAL_BAND)]
        if candidates:
            tx, ty = max(candidates, key=lambda point: (
                weights[point[1]][point[0]] / distances[point[1]][point[0]],
                -diagonal_distance(*point)))
            return actions[ty][tx]

    if opening:
        # Seek a short forward waypoint on the diagonal. BFS permits temporary
        # backward/sideways steps when an obstacle blocks direct progress.
        best = None
        for cy in range(height):
            for cx in range(width):
                distance = distances[cy][cx]
                advance = sx * (cx - ox) + sy * (cy - oy) - progress
                if distance <= 0 or advance <= 0 or distance > state["turns_remaining"]:
                    continue
                enemy = enemy_distances[cy][cx] if enemy_distances else -1
                safety = min(enemy, 8) / 8 if enemy >= 0 else 1.0
                merit = (min(advance, 4) - 2 * diagonal_distance(cx, cy)
                         - distance / 4 + safety / 2)
                if best is None or merit > best[0]:
                    best = (merit, actions[cy][cx])
        if best is not None:
            return best[1]
    return "STAY"
