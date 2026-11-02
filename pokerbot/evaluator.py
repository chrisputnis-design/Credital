"""Fast 5-7 card hand evaluator (pure Python, ~10-20us per call).

evaluate(cards) -> int; higher is better. Category lives in score >> 20:
0 high card, 1 pair, 2 two pair, 3 trips, 4 straight, 5 flush,
6 full house, 7 quads, 8 straight flush.
"""
from __future__ import annotations

# STRAIGHT[mask of 13 rank bits] -> rank index of highest card of the best straight, or -1.
STRAIGHT = [-1] * 8192
for _m in range(8192):
    for _hi in range(12, 3, -1):  # 12 = A-high ... 4 = 6-high
        if all(_m >> (_hi - k) & 1 for k in range(5)):
            STRAIGHT[_m] = _hi
            break
    else:
        if _m & 0b1000000001111 == 0b1000000001111:  # wheel A-2-3-4-5, high card = 5 (idx 3)
            STRAIGHT[_m] = 3

CATEGORY_NAMES = ["high card", "pair", "two pair", "trips", "straight",
                  "flush", "full house", "quads", "straight flush"]


def _top(mask: int, n: int) -> int:
    """Pack the n highest ranks set in mask into 4-bit nibbles."""
    v = 0
    for r in range(12, -1, -1):
        if mask >> r & 1:
            v = v << 4 | r
            n -= 1
            if not n:
                break
    return v


def evaluate(cards) -> int:
    rc = [0] * 13
    sc = [0] * 4
    sm = [0] * 4
    mask = 0
    for c in cards:
        r = c >> 2
        s = c & 3
        rc[r] += 1
        sc[s] += 1
        sm[s] |= 1 << r
        mask |= 1 << r

    fm = 0
    for s in range(4):
        if sc[s] >= 5:
            fm = sm[s]
            break
    if fm:
        sf = STRAIGHT[fm]
        if sf >= 0:
            return 8 << 20 | sf

    quads = -1
    trips = []
    pairs = []
    for r in range(12, -1, -1):
        n = rc[r]
        if n == 4:
            quads = r
        elif n == 3:
            trips.append(r)
        elif n == 2:
            pairs.append(r)

    if quads >= 0:
        kick = _top(mask & ~(1 << quads), 1)
        return 7 << 20 | quads << 4 | kick
    if trips and (len(trips) > 1 or pairs):
        t = trips[0]
        p = max(trips[1:] + pairs)
        return 6 << 20 | t << 4 | p
    if fm:
        return 5 << 20 | _top(fm, 5)
    st = STRAIGHT[mask]
    if st >= 0:
        return 4 << 20 | st
    if trips:
        t = trips[0]
        return 3 << 20 | t << 8 | _top(mask & ~(1 << t), 2)
    if len(pairs) >= 2:
        p1, p2 = pairs[0], pairs[1]
        return 2 << 20 | p1 << 8 | p2 << 4 | _top(mask & ~(1 << p1) & ~(1 << p2), 1)
    if pairs:
        p = pairs[0]
        return 1 << 20 | p << 12 | _top(mask & ~(1 << p), 3)
    return _top(mask, 5)


def category(score: int) -> int:
    return score >> 20
