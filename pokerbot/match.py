"""Run bots against each other.

    python -m pokerbot.match basic callstation --hands 4000
    python -m pokerbot.match basic --vs all
    python -m pokerbot.match my_bot.py:MyBot basic

Duplicate format (default): each deal is played twice with seats swapped, which
cancels most card luck. Result is in big blinds per 100 hands (bb/100), from the
first bot's point of view, with a standard error.
"""
from __future__ import annotations

import argparse
import math
import random
import statistics
import time

from .bots import BOTS, load_bot
from .engine import CALL_ACTION, FOLD_ACTION, play_hand


class TimedBot:
    """Wraps a bot: records decision times, survives exceptions (counts them)."""

    def __init__(self, bot):
        self.bot = bot
        self.times_ns = []
        self.errors = 0
        self.corrections = 0

    def act(self, s):
        t0 = time.perf_counter_ns()
        try:
            a = self.bot.act(s)
        except Exception as e:  # a crash in the real event would likely be a fold
            self.errors += 1
            if self.errors <= 3:
                print(f"  [{getattr(self.bot, 'name', '?')}] exception: {e!r}")
            a = CALL_ACTION if s.to_call == 0 else FOLD_ACTION
        self.times_ns.append(time.perf_counter_ns() - t0)
        return a


def _shuffled(rng):
    d = list(range(52))
    rng.shuffle(d)
    return d


def run_match(cls_a, cls_b, hands=2000, seed=1, stack_bb=100, bb=100, duplicate=True):
    a, b = TimedBot(cls_a()), TimedBot(cls_b())
    rng = random.Random(seed)
    pairs = []
    for _ in range(hands // 2):
        d1 = _shuffled(rng)
        d2 = d1 if duplicate else _shuffled(rng)
        r1 = play_hand((a, b), d1, stack=stack_bb * bb, sb=bb // 2, bb=bb)   # A on button
        r2 = play_hand((b, a), d2, stack=stack_bb * bb, sb=bb // 2, bb=bb)   # B on button
        a.corrections += r1.corrections[0] + r2.corrections[1]
        b.corrections += r1.corrections[1] + r2.corrections[0]
        pairs.append((r1.delta - r2.delta) / bb)
        _notify(a, b, r1, r2)
    n = len(pairs)
    mean = sum(pairs) / n
    sd = statistics.pstdev(pairs) if n > 1 else 0.0
    return {
        "bb_per_100": mean / 2 * 100,
        "stderr": sd / math.sqrt(n) / 2 * 100,
        "hands": n * 2,
        "a": a, "b": b,
    }


def _notify(a, b, r1, r2):
    """Give bots a post-hand summary (opponent modelling hook)."""
    from .engine import HandSummary
    for bot, r, btn in ((a, r1, True), (b, r1, False), (b, r2, True), (a, r2, False)):
        f = getattr(bot.bot, "on_hand_end", None)
        if f is None:
            continue
        p = 0 if btn else 1
        opp_hole = r.hole[1 - p] if r.showdown else None
        try:
            f(HandSummary(my_delta=r.delta if btn else -r.delta, opp_hole=opp_hole,
                          board=r.board, history=r.history, is_button=btn,
                          showdown=r.showdown))
        except Exception:
            bot.errors += 1


def _timing(tb):
    t = sorted(tb.times_ns)
    if not t:
        return "n/a"
    pct = lambda q: t[min(len(t) - 1, int(q * len(t)))] / 1000
    over = sum(1 for x in t if x > 1_000_000)
    return (f"p50 {pct(.5):.0f}us  p99 {pct(.99):.0f}us  max {t[-1] / 1000:.0f}us  "
            f">1ms: {over}")


def report(name_a, name_b, res):
    a, b = res["a"], res["b"]
    print(f"{name_a} vs {name_b}: {res['bb_per_100']:+.1f} bb/100 "
          f"(± {res['stderr']:.1f} se, {res['hands']} hands)")
    print(f"   {name_a:12s} time: {_timing(a)}  errors: {a.errors}  illegal-fixed: {a.corrections}")
    print(f"   {name_b:12s} time: {_timing(b)}  errors: {b.errors}  illegal-fixed: {b.corrections}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bot_a")
    p.add_argument("bot_b", nargs="?")
    p.add_argument("--vs", help="'all' to play bot_a against every builtin bot")
    p.add_argument("--hands", type=int, default=4000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--stack", type=int, default=100, help="starting stack in big blinds")
    p.add_argument("--no-duplicate", action="store_true")
    args = p.parse_args()

    opponents = list(BOTS) if args.vs == "all" else [args.bot_b]
    if opponents == [None]:
        p.error("give bot_b or --vs all")
    cls_a = load_bot(args.bot_a)
    for ob in opponents:
        if ob == args.bot_a:
            continue
        res = run_match(cls_a, load_bot(ob), args.hands, args.seed, args.stack,
                        duplicate=not args.no_duplicate)
        report(args.bot_a, ob, res)


if __name__ == "__main__":
    main()
