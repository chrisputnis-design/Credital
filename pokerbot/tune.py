"""Tune BasicBot parameters by self-play hill-climbing against a pool of opponents.

    python -m pokerbot.tune --iters 300            # writes tuned_params.py
    python -m pokerbot.tune --validate             # fresh-seed check: current vs original params

Each iteration perturbs one parameter and compares candidate vs incumbent on the *same
fresh deals* (common random numbers, new seed every iteration), so we don't overfit one
fixed set of cards. Opponent bots' results are clipped so exploiting dummies can't dominate.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from multiprocessing import Pool

from .basic_bot import DEFAULT_PARAMS, ORIGINAL_PARAMS, BasicBot
from .bots import BOTS
from .match import run_match

POOL = ["basic0", "tight", "loose", "callstation", "maniac", "random"]
CLIP = 120.0

# name -> (lo, hi, step); steps are absolute
BOUNDS = {
    "open_eq": (0.30, 0.75, 0.03), "limp_eq": (0.30, 0.65, 0.03), "iso_eq": (0.45, 0.85, 0.04),
    "open_size": (2.0, 4.0, 0.3), "iso_size": (2.5, 5.0, 0.4),
    "threebet_eq": (0.55, 0.85, 0.03), "threebet_bluff": (0.0, 0.5, 0.05),
    "threebet_size": (2.5, 4.5, 0.3), "fourbet_eq": (0.65, 0.9, 0.03), "pre_margin": (0.0, 0.3, 0.03),
    "value_eq": (0.55, 0.9, 0.03), "value_size": (0.3, 1.2, 0.1), "med_eq": (0.40, 0.75, 0.03),
    "med_size": (0.25, 1.0, 0.1), "med_freq": (0.2, 1.0, 0.1), "weak_eq": (0.2, 0.5, 0.03),
    "weak_freq": (0.0, 1.0, 0.1), "weak_size": (0.25, 1.0, 0.1), "air_freq": (0.0, 0.6, 0.05),
    "air_size": (0.25, 1.0, 0.1), "call_margin": (-0.05, 0.3, 0.03), "raise_eq": (0.75, 0.98, 0.03),
    "raise_mid_freq": (0.0, 1.0, 0.1), "raise_size": (0.4, 1.2, 0.1), "bluff_raise_freq": (0.0, 0.4, 0.04),
}


def _task(args):
    params, adapt, opp, hands, seed = args
    res = run_match(lambda: BasicBot(params=params, adapt=adapt), BOTS[opp], hands, seed)
    return res["bb_per_100"]


def fitness(pool, params, seed, hands, adapt=False, opps=POOL):
    vals = pool.map(_task, [(params, adapt, o, hands, seed) for o in opps])
    return sum(min(v, CLIP) for v in vals) / len(vals), dict(zip(opps, vals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=300)
    ap.add_argument("--hands", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--hands-val", type=int, default=40000)
    args = ap.parse_args()

    with Pool(4) as pool:
        if args.validate:
            validate(pool, args.hands_val)
            return
        rng = random.Random(args.seed)
        best = dict(DEFAULT_PARAMS)
        t0 = time.time()
        accepted = 0
        for it in range(1, args.iters + 1):
            cand = dict(best)
            for k in rng.sample(list(BOUNDS), rng.choice((1, 1, 2))):
                lo, hi, step = BOUNDS[k]
                cand[k] = round(min(hi, max(lo, cand[k] + rng.gauss(0, 1) * step)), 3)
            seed = 1000 + it
            fc, _ = fitness(pool, cand, seed, args.hands)
            fb, _ = fitness(pool, best, seed, args.hands)
            if fc > fb + 0.5:
                best, accepted = cand, accepted + 1
            if it % 10 == 0:
                print(f"iter {it:4d}  accepted {accepted:3d}  last cand {fc:6.1f} vs best {fb:6.1f}"
                      f"  [{time.time() - t0:.0f}s]", flush=True)
        changed = {k: v for k, v in best.items() if v != ORIGINAL_PARAMS[k]}
        path = __file__.replace("tune.py", "tuned_params.py")
        with open(path, "w") as f:
            f.write('"""Output of tune.py (hill-climbed vs a pool of opponents). Overrides ORIGINAL_PARAMS."""\n')
            f.write("TUNED_PARAMS = " + json.dumps(best, indent=4) + "\n")
        print("changed vs original:", json.dumps(changed))


def validate(pool, hands):
    print(f"validation on fresh seeds, {hands} hands per opponent (tuned = current DEFAULT_PARAMS)")
    for name, params in (("original", ORIGINAL_PARAMS), ("tuned", DEFAULT_PARAMS)):
        tot = []
        for seed in (9001, 9002):
            _, per = fitness(pool, params, seed, hands, opps=POOL + ["static"])
            tot.append(per)
        avg = {o: sum(t[o] for t in tot) / len(tot) for o in tot[0]}
        print(f"{name:9s}", "  ".join(f"{o}:{v:+.0f}" for o, v in avg.items()))


if __name__ == "__main__":
    main()
