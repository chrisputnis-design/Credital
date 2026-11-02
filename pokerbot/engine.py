"""Heads-up No-Limit Hold'em engine.

This is a stand-in for the real tournament engine. The variant is revealed on the
day, so everything game-specific is kept here (deal, betting, showdown) and the bots
only see `State` and return an `Action`. When the real API shows up, adapt this file
(and the State fields) and the rest of the sandbox keeps working.

Seats: player 0 = button / small blind (acts first preflop, last postflop),
       player 1 = big blind.
"""
from __future__ import annotations

from .evaluator import evaluate

FOLD, CALL, RAISE = 0, 1, 2  # CALL doubles as CHECK when there is nothing to call
PREFLOP, FLOP, TURN, RIVER = 0, 1, 2, 3
BOARD_LEN = (0, 3, 4, 5)


class Action:
    __slots__ = ("kind", "amount")

    def __init__(self, kind: int, amount: int = 0):
        self.kind = kind
        self.amount = amount  # for RAISE: total bet *this street* to raise to

    def __repr__(self):
        return ("fold", "call", f"raise_to({self.amount})")[self.kind]


FOLD_ACTION = Action(FOLD)
CALL_ACTION = Action(CALL)


def raise_to(amount: int) -> Action:
    return Action(RAISE, int(amount))


class State:
    """Everything a bot may see when it has to act. Chips are ints."""
    __slots__ = ("hole", "board", "street", "pot", "to_call", "my_stack", "opp_stack",
                 "my_bet", "opp_bet", "min_raise_to", "max_raise_to", "can_raise",
                 "is_button", "big_blind", "history")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class HandSummary:
    """Handed to bots after each hand (for opponent modelling)."""
    __slots__ = ("my_delta", "opp_hole", "board", "history", "is_button", "showdown")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class HandResult:
    __slots__ = ("delta", "showdown", "hole", "board", "history", "corrections")

    def __init__(self, delta, showdown, hole, board, history, corrections):
        self.delta = delta            # chips won by player 0 (button); player 1 gets -delta
        self.showdown = showdown
        self.hole = hole
        self.board = board
        self.history = history        # list of (street, player, kind, amount_added)
        self.corrections = corrections  # illegal actions the engine had to fix, per player


def play_hand(bots, deck, stack=10000, sb=50, bb=100) -> HandResult:
    """Play one hand. bots = (button_bot, bb_bot). deck = shuffled list of 52 ints."""
    hole = (tuple(deck[0:2]), tuple(deck[2:4]))
    full_board = tuple(deck[4:9])
    stacks = [stack - sb, stack - bb]
    invested = [sb, bb]
    bet = [sb, bb]
    history = []
    corrections = [0, 0]

    def finish_fold(loser):
        d = invested[loser]
        return HandResult(-d if loser == 0 else d, False, hole, board, history, corrections)

    board = ()
    for street in range(4):
        board = full_board[:BOARD_LEN[street]]
        if street:
            bet = [0, 0]
        if stacks[0] > 0 and stacks[1] > 0:
            cur = 0 if street == PREFLOP else 1
            last_raise = bb
            acted = [False, False]
            while not (acted[0] and acted[1] and bet[0] == bet[1]):
                o = 1 - cur
                if stacks[cur] == 0:
                    acted[cur] = True
                    cur = o
                    continue
                to_call = bet[o] - bet[cur]
                max_to = min(bet[cur] + stacks[cur], bet[o] + stacks[o])
                can_raise = max_to > bet[o]
                min_to = min(bet[o] + last_raise, max_to)
                st = State(hole=hole[cur], board=board, street=street,
                           pot=invested[0] + invested[1], to_call=to_call,
                           my_stack=stacks[cur], opp_stack=stacks[o],
                           my_bet=bet[cur], opp_bet=bet[o],
                           min_raise_to=min_to, max_raise_to=max_to, can_raise=can_raise,
                           is_button=(cur == 0), big_blind=bb,
                           history=tuple((s, p == cur, k, a) for s, p, k, a in history))
                a = bots[cur].act(st)
                kind = a.kind
                if kind == FOLD:
                    if to_call == 0:  # folding for free is a check
                        kind = CALL
                        corrections[cur] += 1
                    else:
                        history.append((street, cur, FOLD, 0))
                        return finish_fold(cur)
                if kind == RAISE and not can_raise:
                    kind = CALL
                    corrections[cur] += 1
                if kind == CALL:
                    add = min(to_call, stacks[cur])
                    stacks[cur] -= add
                    bet[cur] += add
                    invested[cur] += add
                    history.append((street, cur, CALL, add))
                else:
                    to = int(a.amount)
                    if to < min_to or to > max_to:
                        corrections[cur] += 1
                        to = max(min_to, min(to, max_to))
                    add = to - bet[cur]
                    stacks[cur] -= add
                    bet[cur] = to
                    invested[cur] += add
                    last_raise = max(last_raise, to - bet[o])
                    acted[o] = False
                    history.append((street, cur, RAISE, add))
                acted[cur] = True
                cur = o

    s0 = evaluate(hole[0] + full_board)
    s1 = evaluate(hole[1] + full_board)
    # invested is equal for both players at showdown (raises are capped at the effective stack)
    delta = invested[1] if s0 > s1 else (-invested[0] if s0 < s1 else 0)
    return HandResult(delta, True, hole, full_board, history, corrections)
