# pokerbot

Sandbox for the No Limit tournament: a heads-up No-Limit Hold'em engine, a fast hand
evaluator, a baseline bot, and a duplicate-match tester. Pure Python, no dependencies.

The real variant is revealed on the day, so the engine here is a **stand-in**. Everything
game-specific lives in `engine.py`; bots only see a `State` and return an `Action`.

## Run

```bash
python -m pokerbot.match basic --vs all            # basic vs every builtin bot
python -m pokerbot.match basic callstation --hands 20000
python -m pokerbot.match my_bot.py:MyBot basic     # your own bot class from a file
python -m unittest discover -s pokerbot/tests -t . # tests
```

Output is bb/100 from the first bot's side, with a standard error, plus per-bot decision
time (p50/p99/max, count over 1 ms), exceptions, and illegal actions the engine had to fix.
Matches are **duplicate** by default (each deal is played twice with seats swapped), which
removes most card luck. Use `--no-duplicate` if a bot learns from repeated deals.

## Layout

| file | what |
|---|---|
| `evaluator.py` | `evaluate(cards)` for 5–7 cards, higher = better (~5 µs) |
| `engine.py` | `play_hand`, `State`, `Action` (`FOLD`/`CALL`/`RAISE`), blinds, min-raise, all-ins |
| `basic_bot.py` | the baseline bot (`BasicBot`) |
| `bots.py` | dummy opponents (random, callstation, maniac, folder) + loader |
| `match.py` | match runner, timing, stats |
| `gen_preflop.py` | regenerates `preflop_table.py` (equity of 169 hand classes vs random) |

## Bot interface

```python
class MyBot:
    def act(self, s):          # s: State -> Action, must return in < 1 ms
        if s.to_call == 0: return CALL_ACTION          # check
        return raise_to(s.min_raise_to) if s.can_raise else FOLD_ACTION
    def on_hand_end(self, summary): ...   # optional: opp_hole (if showdown), history
```

`State`: `hole`, `board`, `street`, `pot`, `to_call`, `my_stack`, `opp_stack`, `my_bet`,
`opp_bet`, `min_raise_to`, `max_raise_to`, `can_raise`, `is_button`, `big_blind`, `history`.
`raise_to(x)` means "total bet on this street becomes x". Cards are ints (`cards.py`).

## BasicBot

- Preflop: equity-vs-random table + pot odds; opens ~top 60% as SB, 3-bets strong hands.
- Postflop: made-hand + draw strength estimate (no simulation, ~10 µs) + pot odds, some random bluffs.
- Known weaknesses (= the to-do list): ignores board texture and bet size, no opponent
  modelling, thresholds are guesses, hand strength is "vs random" not vs a betting range.

## Caveats

- Timing here is on this machine; the tournament box will differ. Keep a big margin and avoid
  GC pauses (`gc.disable()` in the real submission, precompute tables at import).
- Monte Carlo equity does not fit in 1 ms in pure Python: use lookup tables / heuristics.
- Once the real API/variant is known, adapt `engine.py` and the `State` fields first.
