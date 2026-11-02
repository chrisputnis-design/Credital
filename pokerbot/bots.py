"""Simple opponents to test against, plus a registry/loader."""
from __future__ import annotations

import importlib
import importlib.util
import random

from .basic_bot import BasicBot
from .engine import CALL_ACTION, FOLD_ACTION, raise_to


class RandomBot:
    name = "random"

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def act(self, s):
        r = self.rng.random()
        if r < 0.15 and s.to_call:
            return FOLD_ACTION
        if r < 0.35 and s.can_raise:
            return raise_to(self.rng.randint(s.min_raise_to, s.max_raise_to))
        return CALL_ACTION


class CallStation:
    """Never folds, never raises."""
    name = "callstation"

    def act(self, s):
        return CALL_ACTION


class Maniac:
    """Raises pot-ish every time it can, otherwise calls."""
    name = "maniac"

    def act(self, s):
        if s.can_raise:
            return raise_to(min(s.opp_bet + s.pot, s.max_raise_to))
        return CALL_ACTION


class FoldBot:
    """Folds everything it can (checks when free). Sanity check: should lose blinds."""
    name = "folder"

    def act(self, s):
        return FOLD_ACTION if s.to_call else CALL_ACTION


BOTS = {c.name: c for c in (BasicBot, RandomBot, CallStation, Maniac, FoldBot)}


def load_bot(spec: str):
    """'basic' | 'my_bot.py:MyBot' | 'package.module:MyBot' -> bot class."""
    if spec in BOTS:
        return BOTS[spec]
    if ":" not in spec:
        raise SystemExit(f"unknown bot {spec!r}; builtin: {', '.join(BOTS)} or path.py:Class")
    mod, cls = spec.rsplit(":", 1)
    if mod.endswith(".py"):
        sp = importlib.util.spec_from_file_location("user_bot", mod)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
    else:
        m = importlib.import_module(mod)
    return getattr(m, cls)
