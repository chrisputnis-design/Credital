import unittest

from pokerbot.basic_bot import postflop_strength, preflop_equity
from pokerbot.bots import CallStation, FoldBot, Maniac, RandomBot
from pokerbot.basic_bot import BasicBot
from pokerbot.cards import hand
from pokerbot.match import run_match


class BotTests(unittest.TestCase):
    def test_preflop_equity_ordering(self):
        self.assertGreater(preflop_equity(hand("AsAd")), preflop_equity(hand("KsKd")))
        self.assertGreater(preflop_equity(hand("AsKs")), preflop_equity(hand("AsKd")))
        self.assertGreater(preflop_equity(hand("AsKd")), preflop_equity(hand("7s2d")))

    def test_postflop_strength_sanity(self):
        st = lambda h, b: postflop_strength(hand(h), hand(b))
        self.assertGreater(st("AsAd", "2c7dKh"), st("AsKd", "2c7d9h"))        # overpair > air
        self.assertGreater(st("7s7d", "7c9dKh"), st("AsKd", "Ac9d2h"))        # set > top pair
        self.assertGreater(st("AhKh", "2h7hQc"), st("AsKd", "2h7hQc"))        # flush draw
        self.assertGreater(st("5s6s", "7d8h2c"), st("2s3d", "9d8hKc"))        # open-ender
        self.assertLess(st("2s3d", "AsAdKhQcJd"), 0.5)                         # board plays

    def test_basic_beats_dummies(self):
        for cls in (RandomBot, CallStation, Maniac):
            res = run_match(BasicBot, cls, hands=2000, seed=5)
            self.assertGreater(res["bb_per_100"], 0, cls.name)
            self.assertEqual(res["a"].errors, 0)
            self.assertEqual(res["a"].corrections, 0)

    def test_basic_loses_to_nobody_on_blinds(self):
        res = run_match(BasicBot, FoldBot, hands=1000, seed=2)
        self.assertGreater(res["bb_per_100"], 0)


if __name__ == "__main__":
    unittest.main()
