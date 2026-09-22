"""Strategy regressions; run with python -m unittest discover -s starter-kit."""

import copy
import unittest

import bot


def state(board, position=(0, 0), turn=0, remaining=200):
    return dict(board=board, position=list(position), turn=turn, score=0,
                width=len(board[0]), height=len(board),
                total_turns=turn + remaining, turns_remaining=remaining)


class StrategyTests(unittest.TestCase):
    def setUp(self):
        bot._memory = None

    def test_opening_follows_diagonal_for_40_moves(self):
        board = [[0] * 40 for _ in range(40)]
        x = y = 0
        for turn in range(40):
            action = bot.get_move(state(board, (x, y), turn))
            self.assertIn(action, ("RIGHT", "DOWN"))
            x += action == "RIGHT"
            y += action == "DOWN"
            self.assertLessEqual(abs(x - y), 1)
        self.assertEqual((x, y), (20, 20))

    def test_tracks_opponent_but_not_own_pickup_and_expires(self):
        board = [[0] * 10 for _ in range(10)]
        board[0][1] = board[5][5] = 4
        bot.get_move(state(board))
        board[0][1] = board[5][5] = 0
        bot.get_move(state(board, (1, 0), 1))
        self.assertEqual(bot._memory["opponents"], {(5, 5): 1})
        bot.get_move(state(board, (1, 0), 13))
        self.assertFalse(bot._memory["opponents"])

    def test_snapshot_is_not_mutated_or_aliased(self):
        observation = state([[0, 3], [0, 4]])
        original = copy.deepcopy(observation)
        bot.get_move(observation)
        self.assertEqual(observation, original)
        observation["board"][0][1] = 0
        self.assertEqual(bot._memory["previous"][0][1], 3)

    def test_wall_detour_and_trapped_board(self):
        self.assertEqual(bot.get_move(state([[0, "X", 4], [0, "X", 0], [0, 0, 0]])), "DOWN")
        self.assertEqual(bot.get_move(state([[0, "X"], ["X", 5]])), "STAY")

    def test_last_turn_only_targets_reachable_pickup(self):
        board = [[0] * 10 for _ in range(10)]
        board[5][6] = 3
        board[5][8] = 9
        self.assertEqual(bot.get_move(state(board, (5, 5), 50, 1)), "RIGHT")

    def test_round_reset_forgets_sightings(self):
        board = [[0] * 10 for _ in range(10)]
        bot.get_move(state(board))
        bot._memory["opponents"][(5, 5)] = 0
        bot.get_move(state(board))
        self.assertFalse(bot._memory["opponents"])


if __name__ == "__main__":
    unittest.main()
