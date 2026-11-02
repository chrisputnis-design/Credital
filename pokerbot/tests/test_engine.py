import random
import unittest

from pokerbot.cards import hand
from pokerbot.engine import (CALL_ACTION, FOLD_ACTION, RAISE, PREFLOP, play_hand,
                             raise_to)

BB, SB, STACK = 100, 50, 10000


def deck_for(btn, bbh, board):
    cards = list(hand(btn)) + list(hand(bbh)) + list(hand(board))
    rest = [c for c in range(52) if c not in cards]
    return cards + rest


class Scripted:
    """Plays a fixed list of actions, then calls."""

    def __init__(self, *actions):
        self.actions = list(actions)
        self.seen = []

    def act(self, s):
        self.seen.append(s)
        return self.actions.pop(0) if self.actions else CALL_ACTION


class EngineTests(unittest.TestCase):
    def test_sb_folds_loses_small_blind(self):
        d = deck_for("AsAd", "2c7d", "KhQhJh3c4d")
        r = play_hand((Scripted(FOLD_ACTION), Scripted()), d, STACK, SB, BB)
        self.assertEqual(r.delta, -SB)
        self.assertFalse(r.showdown)

    def test_bb_folds_to_raise_loses_big_blind(self):
        d = deck_for("AsAd", "2c7d", "KhQhJh3c4d")
        r = play_hand((Scripted(raise_to(300)), Scripted(FOLD_ACTION)), d, STACK, SB, BB)
        self.assertEqual(r.delta, BB)

    def test_limp_check_to_showdown_best_hand_wins(self):
        d = deck_for("AsAd", "2c7d", "KhQh9s3c4d")
        r = play_hand((Scripted(), Scripted()), d, STACK, SB, BB)
        self.assertTrue(r.showdown)
        self.assertEqual(r.delta, BB)
        d = deck_for("2c7d", "AsAd", "KhQh9s3c4d")
        r = play_hand((Scripted(), Scripted()), d, STACK, SB, BB)
        self.assertEqual(r.delta, -BB)

    def test_split_pot(self):
        d = deck_for("2c3d", "2h3s", "AsKsQsJsTs")  # royal flush on board
        r = play_hand((Scripted(), Scripted()), d, STACK, SB, BB)
        self.assertEqual(r.delta, 0)

    def test_all_in_and_call(self):
        d = deck_for("AsAd", "2c7d", "KhQh9s3c4d")
        r = play_hand((Scripted(raise_to(10**9)), Scripted()), d, STACK, SB, BB)
        self.assertEqual(r.delta, STACK)
        d = deck_for("2c7d", "AsAd", "KhQh9s3c4d")
        r = play_hand((Scripted(raise_to(10**9)), Scripted()), d, STACK, SB, BB)
        self.assertEqual(r.delta, -STACK)

    def test_min_raise_clamped_and_reported(self):
        d = deck_for("AsAd", "2c7d", "KhQh9s3c4d")
        b = Scripted(raise_to(101))  # below min raise (to 200)
        o = Scripted(FOLD_ACTION)
        r = play_hand((b, o), d, STACK, SB, BB)
        self.assertEqual(o.seen[0].opp_bet, 200)
        self.assertEqual(r.corrections[0], 1)

    def test_state_fields_preflop(self):
        d = deck_for("AsAd", "2c7d", "KhQh9s3c4d")
        b, o = Scripted(raise_to(300)), Scripted(FOLD_ACTION)
        play_hand((b, o), d, STACK, SB, BB)
        s = b.seen[0]
        self.assertEqual((s.street, s.pot, s.to_call, s.is_button), (PREFLOP, 150, 50, True))
        self.assertEqual((s.min_raise_to, s.max_raise_to), (200, STACK))
        t = o.seen[0]
        self.assertEqual((t.pot, t.to_call, t.opp_bet, t.my_bet), (400, 200, 300, 100))
        self.assertEqual(t.min_raise_to, 500)  # opp bet 300 + last raise 200
        self.assertEqual(t.history[-1][2], RAISE)

    def test_free_fold_becomes_check(self):
        d = deck_for("AsAd", "2c7d", "KhQh9s3c4d")
        r = play_hand((Scripted(CALL_ACTION), Scripted(FOLD_ACTION)), d, STACK, SB, BB)
        self.assertTrue(r.showdown)
        self.assertEqual(r.corrections[1], 1)

    def test_chips_conserved_random_play(self):
        from pokerbot.bots import RandomBot, Maniac, CallStation
        rng = random.Random(3)
        bots = [RandomBot(1), RandomBot(2), Maniac(), CallStation()]
        for _ in range(500):
            deck = list(range(52))
            rng.shuffle(deck)
            a, b = rng.sample(bots, 2)
            r = play_hand((a, b), deck, STACK, SB, BB)
            self.assertLessEqual(abs(r.delta), STACK)
            self.assertNotEqual(r.delta, 0) if not r.showdown else None


if __name__ == "__main__":
    unittest.main()
