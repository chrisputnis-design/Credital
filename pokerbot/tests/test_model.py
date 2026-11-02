import unittest

from pokerbot.basic_bot import BasicBot, OpponentModel
from pokerbot.bots import CallStation, Maniac, Tight
from pokerbot.engine import CALL, FOLD, RAISE, HandSummary
from pokerbot.match import run_match


def summ(history, is_button=True):
    return HandSummary(my_delta=0, opp_hole=None, board=(), history=history,
                       is_button=is_button, showdown=False)


class ModelTests(unittest.TestCase):
    def test_counts_open_fold_and_postflop_fold(self):
        m = OpponentModel()
        m.update(summ([(0, 0, RAISE, 250), (0, 1, FOLD, 0)]))
        self.assertEqual((m.pre_open_faced, m.pre_open_folds), (1, 1))
        m.update(summ([(0, 0, RAISE, 250), (0, 1, CALL, 150), (1, 1, CALL, 0),
                       (1, 0, RAISE, 100), (1, 1, FOLD, 0)]))
        self.assertEqual((m.pre_open_faced, m.pre_open_folds), (2, 1))
        self.assertEqual((m.post_bets_faced, m.post_bet_folds, m.post_opp_calls), (1, 1, 1))

    def test_seat_perspective(self):
        m = OpponentModel()  # we are the BB (player 1), opp (button) opens: not our open
        m.update(summ([(0, 0, RAISE, 250), (0, 1, FOLD, 0)], is_button=False))
        self.assertEqual(m.pre_open_faced, 0)

    def test_opp_raise_is_not_response_to_our_bet(self):
        m = OpponentModel()
        m.update(summ([(1, 1, RAISE, 100), (1, 0, CALL, 100)]))
        self.assertEqual((m.post_bets_faced, m.post_opp_raises), (0, 1))

    def test_rates_are_smoothed_toward_prior(self):
        m = OpponentModel()
        self.assertAlmostEqual(m.fold_to_bet, 0.40)
        m.post_bets_faced, m.post_bet_folds = 200, 0
        self.assertLess(m.fold_to_bet, 0.05)

    def test_adjustments_neutral_until_enough_hands(self):
        b = BasicBot()
        self.assertEqual(b._adj(), (1.0, 0.0, 0.0, 0.0))

    def test_adaptation_never_hurts_much_and_exploits_stations(self):
        ada = run_match(lambda: BasicBot(adapt=True), CallStation, hands=6000, seed=3)
        sta = run_match(lambda: BasicBot(adapt=False), CallStation, hands=6000, seed=3)
        self.assertGreater(ada["bb_per_100"], sta["bb_per_100"] - 15)


if __name__ == "__main__":
    unittest.main()
