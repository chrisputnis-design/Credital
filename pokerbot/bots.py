"""Simple opponents to test against, plus a registry/loader."""
from __future__ import annotations

import importlib
import importlib.util
import random

from .basic_bot import ORIGINAL_PARAMS, BasicBot
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


class _Preset(BasicBot):
    """BasicBot with fixed parameter overrides and no adaptation (a 'style' to test against)."""
    overrides: dict = {}

    def __init__(self, seed: int = 0):
        super().__init__(seed=seed, params=self.overrides, adapt=False)


class Basic0(_Preset):
    """The original hand-guessed BasicBot: the baseline every tuning step must beat."""
    name = "basic0"
    overrides = ORIGINAL_PARAMS


class Static(_Preset):
    """Current (tuned) parameters but no opponent modelling."""
    name = "static"


class Tight(_Preset):
    """Nit: plays few hands, folds to pressure, rarely bluffs."""
    name = "tight"
    overrides = dict(open_eq=0.60, limp_eq=0.50, iso_eq=0.70, threebet_eq=0.78,
                     threebet_bluff=0.0, pre_margin=0.20, call_margin=0.18, value_eq=0.78,
                     med_eq=0.64, weak_freq=0.08, air_freq=0.02, bluff_raise_freq=0.0)


class Loose(_Preset):
    """Loose-aggressive: wide ranges, lots of bluffs and raises."""
    name = "loose"
    overrides = dict(open_eq=0.42, limp_eq=0.34, iso_eq=0.50, threebet_eq=0.62,
                     threebet_bluff=0.20, pre_margin=0.06, call_margin=0.03, value_eq=0.62,
                     med_eq=0.45, weak_freq=0.5, air_freq=0.35, bluff_raise_freq=0.15,
                     raise_mid_freq=0.6)


BOTS = {c.name: c for c in (BasicBot, Basic0, Static, Tight, Loose, RandomBot,
                            CallStation, Maniac, FoldBot)}


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
