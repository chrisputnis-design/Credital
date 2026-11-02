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


# Original hand-guessed thresholds (kept as the baseline to beat).
ORIGINAL_PARAMS = dict(
    open_eq=0.52, limp_eq=0.40, iso_eq=0.62, open_size=2.5, iso_size=3.0,
    threebet_eq=0.72, threebet_bluff=0.08, threebet_size=3.2,
    fourbet_eq=0.78, pre_margin=0.14,
    value_eq=0.72, value_size=0.7, med_eq=0.55, med_size=0.5, med_freq=0.7,
    weak_eq=0.35, weak_freq=0.25, weak_size=0.4, air_freq=0.10, air_size=0.4,
    call_margin=0.10, raise_eq=0.85, raise_mid_freq=0.4, raise_size=0.75,
    bluff_raise_freq=0.05,
)
DEFAULT_PARAMS = dict(ORIGINAL_PARAMS)  # overwritten below by tuned values (tuned_params.py)
try:
    from .tuned_params import TUNED_PARAMS
    DEFAULT_PARAMS.update(TUNED_PARAMS)
except ImportError:
    pass


class OpponentModel:
    """Smoothed frequencies of what the opponent does, from on_hand_end summaries."""

    def __init__(self):
        self.hands = 0
        self.pre_open_faced = 0     # times we raised preflop (unraised pot) and opp responded
        self.pre_open_folds = 0
        self.post_bets_faced = 0    # opp responses to our postflop bet/raise
        self.post_bet_folds = 0
        self.post_opp_raises = 0    # opp postflop aggressive actions vs passive
        self.post_opp_calls = 0

    def update(self, summary):
        me = 0 if summary.is_button else 1
        self.hands += 1
        cur_street = -1
        last_raiser = None   # who made the latest raise on the current street
        pre_raises = 0
        for street, pl, kind, _amt in summary.history:
            if street != cur_street:
                cur_street, last_raiser = street, None
            if pl != me:
                if street == 0:
                    if last_raiser == me and pre_raises == 1:   # response to our open
                        self.pre_open_faced += 1
                        self.pre_open_folds += kind == 0
                else:
                    if last_raiser == me:                       # response to our bet
                        self.post_bets_faced += 1
                        self.post_bet_folds += kind == 0
                    if kind == RAISE:
                        self.post_opp_raises += 1
                    elif kind == 1:
                        self.post_opp_calls += 1
            if kind == RAISE:
                last_raiser = pl
                if street == 0:
                    pre_raises += 1

    @staticmethod
    def _rate(k, n, prior, w=20):
        return (k + prior * w) / (n + w)

    @property
    def fold_to_bet(self):  # postflop
        return self._rate(self.post_bet_folds, self.post_bets_faced, 0.40)

    @property
    def fold_to_open(self):
        return self._rate(self.pre_open_folds, self.pre_open_faced, 0.35)

    @property
    def aggression(self):
        return self._rate(self.post_opp_raises, self.post_opp_raises + self.post_opp_calls, 0.35)


class BasicBot:
    name = "basic"

    def __init__(self, seed: int = 0, params=None, adapt: bool = True):
        self.rng = random.Random(seed)
        self.p = dict(DEFAULT_PARAMS)
        if params:
            self.p.update(params)
        self.adapt = adapt
        self.model = OpponentModel()

    def on_hand_end(self, summary) -> None:
        if self.adapt:
            self.model.update(summary)

    def act(self, s):
        if s.street == 0:
            return self._preflop(s)
        return self._postflop(s)

    # --- exploit adjustments (neutral until enough hands are seen) ---
    def _adj(self):
        """Returns (bluff_mult, open_shift, margin_shift, value_shift)."""
        m = self.model
        if not self.adapt or m.hands < 60:
            return 1.0, 0.0, 0.0, 0.0
        f = m.fold_to_bet
        bluff = max(0.0, min(3.0, (f - 0.15) / 0.25))      # folds a lot -> bluff more, never vs stations
        open_shift = -0.10 * max(-1.0, min(1.0, (m.fold_to_open - 0.35) / 0.3))
        margin = -0.06 * max(-1.0, min(1.0, (m.aggression - 0.35) / 0.3))  # maniac -> call lighter
        value = -0.06 * max(0.0, min(1.0, (0.35 - f) / 0.25))             # stations -> value bet thinner
        return bluff, open_shift, margin, value

    # ------------------------------------------------------------------
    def _preflop(self, s):
        p = self.p
        bluff, open_shift, margin, _ = self._adj()
        eq = preflop_equity(s.hole)
        bb = s.big_blind
        c = s.to_call
        pot = s.pot
        n_raises = sum(1 for h in s.history if h[2] == RAISE)
        r = self.rng.random()

        if n_raises == 0:
            if s.is_button:  # small blind, first to act
                if eq >= p["open_eq"] + open_shift:
                    return raise_to(s, p["open_size"] * bb)
                return CALL_ACTION if eq >= p["limp_eq"] else FOLD_ACTION
            return raise_to(s, p["iso_size"] * bb) if eq >= p["iso_eq"] else CALL_ACTION

        odds = c / (pot + c) if c else 0.0
        pm = p["pre_margin"] + margin
        if n_raises == 1:  # facing an open
            if eq >= p["threebet_eq"] or (eq >= 0.50 and r < p["threebet_bluff"] * bluff):
                return raise_to(s, p["threebet_size"] * s.opp_bet)
            return CALL_ACTION if eq >= odds + pm else FOLD_ACTION
        if eq >= p["fourbet_eq"]:  # facing a 3-bet or more
            return raise_to(s, s.max_raise_to if s.opp_bet > 0.2 * (s.my_bet + s.my_stack)
                            else 2.3 * s.opp_bet)
        return CALL_ACTION if eq >= odds + pm else FOLD_ACTION

    # ------------------------------------------------------------------
    def _postflop(self, s):
        p = self.p
        bluff, _, margin, value = self._adj()
        st = postflop_strength(s.hole, s.board)
        pot = s.pot
        c = s.to_call
        r = self.rng.random()

        if c == 0:
            if st >= p["value_eq"] + value:
                return raise_to(s, p["value_size"] * pot)
            if st >= p["med_eq"] + value:
                return raise_to(s, p["med_size"] * pot) if r < p["med_freq"] else CALL_ACTION
            if st >= p["weak_eq"]:
                return raise_to(s, p["weak_size"] * pot) if r < p["weak_freq"] * bluff else CALL_ACTION
            return raise_to(s, p["air_size"] * pot) if r < p["air_freq"] * bluff else CALL_ACTION

        odds = c / (pot + c)
        if st >= p["raise_eq"] or (st >= p["value_eq"] and r < p["raise_mid_freq"]):
            return raise_to(s, s.opp_bet + p["raise_size"] * (pot + c))
        if st >= odds + p["call_margin"] + margin:
            return CALL_ACTION
        if r < p["bluff_raise_freq"] * bluff and c <= 0.5 * pot:
            return raise_to(s, s.opp_bet + p["raise_size"] * (pot + c))
        return FOLD_ACTION
