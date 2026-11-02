"""BasicBot: a simple rule-based starting point to improve on.

Preflop: hand-class equity vs a random hand (precomputed table) + pot odds.
Postflop: crude made-hand/draw strength estimate + pot odds, with some randomised
bluffs. No Monte Carlo (1 ms budget in pure Python), no opponent modelling yet.

Ideas to improve (see README): board-texture awareness, bet-size reading,
opponent stats via on_hand_end(), better draw/kicker handling, mixed strategies.
"""
from __future__ import annotations

import random

from .engine import CALL_ACTION, FOLD_ACTION, RAISE
from .engine import raise_to as _raise_to
from .evaluator import STRAIGHT, evaluate
from .preflop_table import PREFLOP_EQUITY
from .cards import RANKS


def raise_to(s, amount):
    """Legal raise (clamped to min/max), or a call/check if raising is not possible."""
    if not s.can_raise:
        return CALL_ACTION
    return _raise_to(max(s.min_raise_to, min(int(amount), s.max_raise_to)))


def preflop_equity(hole) -> float:
    a, b = hole[0] >> 2, hole[1] >> 2
    if a < b:
        a, b = b, a
    if a == b:
        key = RANKS[a] * 2
    else:
        key = RANKS[a] + RANKS[b] + ("s" if hole[0] & 3 == hole[1] & 3 else "o")
    return PREFLOP_EQUITY[key]


def postflop_strength(hole, board) -> float:
    """Rough 0..1 'how good is my hand' (roughly equity-like). Fast, not exact."""
    score = evaluate(hole + board)
    cat = score >> 20
    h0, h1 = hole[0] >> 2, hole[1] >> 2
    nb = len(board)
    bmax = max(c >> 2 for c in board)
    made = 0.2

    if nb == 5 and score == evaluate(board):
        made = 0.3  # we are just playing the board
    elif cat == 0:
        made = 0.30 if max(h0, h1) == 12 else (0.26 if max(h0, h1) == 11 else 0.2)
    elif cat == 1:
        pr = score >> 12 & 0xF
        if pr != h0 and pr != h1:
            made = 0.28  # pair is on the board
        elif h0 == h1:
            made = 0.75 if pr > bmax else 0.5
        else:
            others = sorted({c >> 2 for c in board}, reverse=True)
            if pr == others[0]:
                kick = h1 if pr == h0 else h0
                made = 0.62 + (0.05 if kick >= 11 else 0.0)
            elif len(others) > 1 and pr == others[1]:
                made = 0.48
            else:
                made = 0.38
    elif cat == 2:
        p1, p2 = score >> 8 & 0xF, score >> 4 & 0xF
        used = (p1 == h0 or p1 == h1) + (p2 == h0 or p2 == h1)
        made = (0.35, 0.68, 0.82)[used]
    elif cat == 3:
        t = score >> 8 & 0xF
        made = 0.88 if (t == h0 or t == h1) else 0.4
    elif cat == 4:
        made = 0.9
    elif cat == 5:
        made = 0.93
    elif cat == 6:
        made = 0.97
    else:
        made = 0.99

    if nb < 5 and cat < 4:  # draws only matter if there are cards to come
        outs = 0
        cards = hole + board
        for s in range(4):
            n = 0
            mine = False
            for c in cards:
                if c & 3 == s:
                    n += 1
                    if c in hole:
                        mine = True
            if n == 4 and mine:
                outs += 9
        bm = 0
        for c in board:
            bm |= 1 << (c >> 2)
        am = bm | 1 << h0 | 1 << h1
        if STRAIGHT[am] < 0:
            n_out_ranks = 0
            for r in range(13):
                if not am >> r & 1 and STRAIGHT[am | 1 << r] >= 0 and STRAIGHT[bm | 1 << r] < 0:
                    n_out_ranks += 1
            outs += 4 * min(n_out_ranks, 2)
        if outs:
            draw = min(0.65, 0.06 + outs * (0.04 if nb == 3 else 0.022))
            made = max(made, draw)
    return made


class BasicBot:
    name = "basic"

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    # --- optional hook: called after every hand (use for opponent modelling) ---
    def on_hand_end(self, summary) -> None:
        pass

    def act(self, s):
        if s.street == 0:
            return self._preflop(s)
        return self._postflop(s)

    # ------------------------------------------------------------------
    def _preflop(self, s):
        eq = preflop_equity(s.hole)
        bb = s.big_blind
        c = s.to_call
        pot = s.pot
        n_raises = sum(1 for h in s.history if h[2] == RAISE)
        r = self.rng.random()

        if n_raises == 0:
            if s.is_button:  # small blind, first to act
                if eq >= 0.52:
                    return raise_to(s, 2.5 * bb)
                return CALL_ACTION if eq >= 0.40 else FOLD_ACTION
            # big blind after a limp
            return raise_to(s, 3 * bb) if eq >= 0.62 else CALL_ACTION

        odds = c / (pot + c) if c else 0.0
        if n_raises == 1:  # facing an open
            if eq >= 0.72 or (eq >= 0.50 and r < 0.08):
                return raise_to(s, 3.2 * s.opp_bet)
            return CALL_ACTION if eq >= odds + 0.14 else FOLD_ACTION
        # facing a 3-bet or more
        if eq >= 0.78:
            return raise_to(s, s.max_raise_to if s.opp_bet > 0.2 * (s.my_bet + s.my_stack)
                            else 2.3 * s.opp_bet)
        return CALL_ACTION if eq >= odds + 0.14 else FOLD_ACTION

    # ------------------------------------------------------------------
    def _postflop(self, s):
        st = postflop_strength(s.hole, s.board)
        pot = s.pot
        c = s.to_call
        r = self.rng.random()

        if c == 0:
            if st >= 0.72:
                return raise_to(s, 0.7 * pot)
            if st >= 0.55:
                return raise_to(s, 0.5 * pot) if r < 0.7 else CALL_ACTION
            if st >= 0.35:
                return raise_to(s, 0.4 * pot) if r < 0.25 else CALL_ACTION
            return raise_to(s, 0.4 * pot) if r < 0.10 else CALL_ACTION

        odds = c / (pot + c)
        if st >= 0.85 or (st >= 0.72 and r < 0.4):
            return raise_to(s, s.opp_bet + 0.75 * (pot + c))
        if st >= odds + 0.10:
            return CALL_ACTION
        if r < 0.05 and c <= 0.5 * pot:
            return raise_to(s, s.opp_bet + 0.75 * (pot + c))  # occasional bluff-raise
        return FOLD_ACTION
