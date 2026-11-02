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
python -m pokerbot.tune --validate                # fresh-seed check of tuned vs original
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

- Preflop: equity-vs-random table + pot odds. Postflop: made-hand + draw strength estimate
  (no simulation, ~10 µs) + pot odds, some random bluffs. All thresholds live in a params dict.
- `tuned_params.py` holds thresholds hill-climbed by self-play (`python -m pokerbot.tune`).
  `ORIGINAL_PARAMS` is the hand-guessed version, kept as the baseline (`basic0`).
- Opponent model (`OpponentModel`, fed by `on_hand_end`): smoothed fold-to-bet, fold-to-open,
  aggression. Only two adjustments are on by default, because they were the only ones that paid:
  call lighter vs aggressive opponents (`margin`), bet thinner vs stations (`value`).
  `bluff` (bluff more vs folders) and `open` (open wider vs folders) *lost* money when tested,
  so they are opt-in: `BasicBot(adapt=("bluff",))`.

Opponent presets for testing: `basic0`, `static` (tuned, no model), `tight`, `loose`,
`callstation`, `maniac`, `random`, `folder`.

### Measured (bb/100, duplicate, 20k–80k hands, fresh seeds; ± ≈ 5–25)

| basic vs | result | note |
|---|---|---|
| basic0 (original) | +11 ± 7 | tuned+model vs hand-guessed; tuned params alone were +16 head-to-head |
| static (no model) | −4 ± 5 | model is not a gain vs a same-strength opponent |
| tight | −9 ± 6 | **loses slightly to the nit** |
| loose | +96 | |
| callstation | +410 | |
| maniac | +840 | was +490 without the model |

Honest read: the tuning is a modest gain and was fit to a pool of *my own* bots, so it says
little about the real field. The model's value is exploiting extremes (maniac, station).
Tuning hurts vs maniac if you look unclipped (+803 original → +490 tuned-static).

## Tuning

`python -m pokerbot.tune --iters 400` perturbs one param at a time and keeps it if it wins on
fresh deals vs a pool (basic0, tight, loose, callstation, maniac, random; results clipped at
120 so dummies don't dominate). `--validate` re-checks on unseen seeds. Takes ~11 min on 4 cores.

## Caveats

- Timing here is on this machine; the tournament box will differ. Keep a big margin and avoid
  GC pauses (`gc.disable()` in the real submission, precompute tables at import).
- Monte Carlo equity does not fit in 1 ms in pure Python: use lookup tables / heuristics.
- Once the real API/variant is known, adapt `engine.py` and the `State` fields first.
