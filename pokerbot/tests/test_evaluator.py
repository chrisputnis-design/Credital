import itertools
import random
import unittest
from collections import Counter

from pokerbot.cards import hand
from pokerbot.evaluator import evaluate


def slow5(cards):
    """Independent 5-card evaluator (tuple-based) used as a reference."""
    ranks = sorted((c >> 2 for c in cards), reverse=True)
    flush = len({c & 3 for c in cards}) == 1
    uniq = sorted(set(ranks), reverse=True)
    straight_hi = None
    if len(uniq) == 5:
        if uniq[0] - uniq[4] == 4:
            straight_hi = uniq[0]
        elif uniq == [12, 3, 2, 1, 0]:
            straight_hi = 3
    cnt = Counter(ranks)
    groups = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    shape = [n for _, n in groups]
    order = [r for r, _ in groups]
    if straight_hi is not None and flush:
        return (8, straight_hi)
    if shape == [4, 1]:
        return (7, *order)
    if shape == [3, 2]:
        return (6, *order)
    if flush:
        return (5, *ranks)
    if straight_hi is not None:
        return (4, straight_hi)
    if shape == [3, 1, 1]:
        return (3, *order)
    if shape == [2, 2, 1]:
        return (2, *order)
    if shape == [2, 1, 1, 1]:
        return (1, *order)
    return (0, *ranks)


def slow7(cards):
    return max(slow5(c) for c in itertools.combinations(cards, 5))


class EvaluatorTests(unittest.TestCase):
    def test_category_ordering(self):
        hands = ["AsKsQsJsTs", "9h9d9c9s2c", "KhKdKcQsQd", "2h5h9hJhKh", "5c6d7h8s9c",
                 "QcQdQhAs3c", "AcAdKhQs3c", "JcJdTh9s2c", "AcKdJh9s2c"]
        scores = [evaluate(hand(h)) for h in hands]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(len(set(scores)), len(scores))

    def test_wheel_is_lowest_straight(self):
        self.assertLess(evaluate(hand("Ac2d3h4s5c")), evaluate(hand("2c3d4h5s6c")))

    def test_kickers(self):
        self.assertGreater(evaluate(hand("AcAdKh7s2c")), evaluate(hand("AcAdQh7s2c")))
        self.assertEqual(evaluate(hand("AcAdKh7s2c")), evaluate(hand("AhAsKd7c2d")))

    def test_matches_reference_on_random_7_card_hands(self):
        rng = random.Random(7)
        deck = list(range(52))
        pairs = []
        for _ in range(3000):
            x = rng.sample(deck, 7)
            y = rng.sample(deck, 7)
            pairs.append((x, y))
        for x, y in pairs:
            fx, fy = evaluate(x), evaluate(y)
            sx, sy = slow7(x), slow7(y)
            self.assertEqual((fx > fy) - (fx < fy), (sx > sy) - (sx < sy), (x, y))
            self.assertEqual(fx >> 20, sx[0])

    def test_matches_reference_on_5_and_6_cards(self):
        rng = random.Random(8)
        for n in (5, 6):
            for _ in range(500):
                x, y = rng.sample(range(52), n), rng.sample(range(52), n)
                fx, fy = evaluate(x), evaluate(y)
                sx = max(slow5(c) for c in itertools.combinations(x, 5))
                sy = max(slow5(c) for c in itertools.combinations(y, 5))
                self.assertEqual((fx > fy) - (fx < fy), (sx > sy) - (sx < sy))


if __name__ == "__main__":
    unittest.main()
