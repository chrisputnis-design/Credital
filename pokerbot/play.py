"""Play heads-up against a bot in the terminal.

    python -m pokerbot.play                 # vs the current basic bot
    python -m pokerbot.play maniac          # vs any bot name / path.py:Class
    python -m pokerbot.play --seed 7        # reproducible deals

Commands:  f fold | c check/call | r <bb> raise TO that many bb this street
           p pot-size raise | a all-in | q quit
Stacks reset to 100 bb every hand; the button alternates.
"""
from __future__ import annotations

import argparse
import random

from .bots import load_bot
from .cards import cards_str
from .engine import CALL, CALL_ACTION, FOLD, FOLD_ACTION, RAISE, HandSummary, play_hand, raise_to

STREETS = ("Preflop", "Flop", "Turn", "River")


class Quit(Exception):
    pass


class Human:
    name = "you"

    def __init__(self, bb):
        self.bb = bb
        self.shown = 0
        self.street = -1

    def new_hand(self, is_button):
        self.shown, self.street = 0, -1
        # chips each side has in on the current street (blinds preflop)
        self.bets = {True: self.bb // 2 if is_button else self.bb,
                     False: self.bb if is_button else self.bb // 2}

    def fmt(self, chips):
        v = chips / self.bb
        return f"{v:g}bb"

    def show_actions(self, history, mine):
        """Print actions not yet shown. mine(player/actor) -> bool."""
        for street, who, kind, amt in history[self.shown:]:
            if street != self.street:
                self.street = street
                if street:
                    self.bets = {True: 0, False: 0}
            m = bool(mine(who))
            self.bets[m] += amt
            who_s = "You" if m else "Bot"
            verb = {FOLD: "folds", CALL: "checks" if amt == 0 else f"calls {self.fmt(amt)}",
                    RAISE: f"{'raises' if self.bets[not m] else 'bets'} to {self.fmt(self.bets[m])}"}[kind]
            print(f"   {STREETS[street]:7s} {who_s} {verb}")
        self.shown = len(history)

    def act(self, s):
        self.show_actions(s.history, mine=lambda w: w)
        print(f"\n  {STREETS[s.street]}  board: {cards_str(s.board) or '-'}   "
              f"your hand: {cards_str(s.hole)}   {'(button)' if s.is_button else '(big blind)'}")
        print(f"  pot {self.fmt(s.pot)}  to call {self.fmt(s.to_call)}  "
              f"your stack {self.fmt(s.my_stack)}  bot stack {self.fmt(s.opp_stack)}")
        while True:
            try:
                raw = input("  > ").strip().lower()
            except EOFError:
                raise Quit
            if raw in ("q", "quit"):
                raise Quit
            if raw in ("f", "fold"):
                if s.to_call == 0:
                    print("  nothing to call, checking")
                    return CALL_ACTION
                return FOLD_ACTION
            if raw in ("c", "call", "check", ""):
                return CALL_ACTION
            if raw in ("a", "allin", "all-in") and s.can_raise:
                return raise_to(s.max_raise_to)
            if raw in ("p", "pot") and s.can_raise:
                return self._clamp(s, s.opp_bet + s.pot + s.to_call)
            if raw.startswith("r") and s.can_raise:
                try:
                    amt = float(raw.split()[1]) * self.bb
                except (IndexError, ValueError):
                    print("  usage: r <bb>   e.g. r 6")
                    continue
                return self._clamp(s, amt, warn=True)
            print("  f / c / r <bb> / p / a / q" + ("" if s.can_raise else "   (you cannot raise)"))

    def _clamp(self, s, amt, warn=False):
        to = max(s.min_raise_to, min(int(amt), s.max_raise_to))
        if warn and to != int(amt):
            print(f"  raise must be between {self.fmt(s.min_raise_to)} and {self.fmt(s.max_raise_to)}; using {self.fmt(to)}")
        return raise_to(to)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bot", nargs="?", default="basic")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--stack", type=int, default=100, help="stack in big blinds")
    args = ap.parse_args()

    bb = 100
    rng = random.Random(args.seed)
    bot = load_bot(args.bot)()
    me = Human(bb)
    total, n = 0.0, 0
    print(f"Heads-up vs '{args.bot}', {args.stack}bb stacks, blinds 0.5/1bb. 'q' to quit.")
    try:
        while True:
            n += 1
            deck = list(range(52))
            rng.shuffle(deck)
            you_btn = n % 2 == 1
            me.new_hand(you_btn)
            print(f"\n=== Hand {n}  ({'you are on the button/SB' if you_btn else 'bot is on the button/SB'}) ===")
            bots = (me, bot) if you_btn else (bot, me)
            r = play_hand(bots, deck, stack=args.stack * bb, sb=bb // 2, bb=bb)
            my_idx = 0 if you_btn else 1
            me.show_actions(r.history, mine=lambda w: w == my_idx)
            delta = (r.delta if you_btn else -r.delta) / bb
            total += delta
            if r.showdown:
                print(f"\n  Showdown  board: {cards_str(r.board)}")
                print(f"  you: {cards_str(r.hole[my_idx])}   bot: {cards_str(r.hole[1 - my_idx])}")
            print(f"  >> {'You win' if delta > 0 else 'You lose' if delta < 0 else 'Split'} "
                  f"{abs(delta):g}bb   | session: {total:+g}bb over {n} hands")
            f = getattr(bot, "on_hand_end", None)
            if f:
                f(HandSummary(my_delta=-delta * bb, opp_hole=r.hole[my_idx] if r.showdown else None,
                              board=r.board, history=r.history, is_button=not you_btn,
                              showdown=r.showdown))
    except (Quit, KeyboardInterrupt):
        n_done = max(n - 1, 0)
        print(f"\nBye. Session: {total:+g}bb over {n_done} completed hands"
              + (f" ({total / n_done * 100:+.0f} bb/100)." if n_done else "."))


if __name__ == "__main__":
    main()
