import json
import pathlib
import random
import shutil
import subprocess
import unittest

from pokerbot.basic_bot import postflop_strength, preflop_equity
from pokerbot.bots import CallStation, Maniac
from pokerbot.engine import play_hand
from pokerbot.evaluator import evaluate

WEB = pathlib.Path(__file__).parent.parent / "web"

JS = """
const P = require(process.argv[2] + "/poker.js")(require(process.argv[2] + "/data.json"));
const ref = JSON.parse(require("fs").readFileSync(0, "utf8"));
let bad = 0;
for (const [x, s] of ref.ev) if (P.evaluate(x) !== s) bad++;
for (const [h, b, s, e] of ref.st) if (Math.abs(P.postflopStrength(h, b) - s) > 1e-9 || Math.abs(P.preflopEquity(h) - e) > 1e-9) bad++;
const run = (d, bots) => { const g = P.playHand(d, 10000, 50, 100); let r = g.next();
  while (!r.done) r = g.next(bots[r.value.cur].act(r.value.state)); return r.value.delta; };
const man = { act: (s) => (s.canRaise ? P.raiseTo(Math.min(s.oppBet + s.pot, s.maxRaiseTo)) : P.CALL_A) };
const cs = { act: () => P.CALL_A };
for (const [d, r1, r2] of ref.hands) if (run(d, [man, cs]) !== r1 || run(d, [cs, man]) !== r2) bad++;
console.log(bad);
"""


@unittest.skipUnless(shutil.which("node"), "node not installed")
class WebParityTests(unittest.TestCase):
    def test_js_port_matches_python(self):
        rng = random.Random(1)
        ev = [[x, evaluate(x)] for x in (rng.sample(range(52), 7) for _ in range(3000))]
        st = []
        for _ in range(1000):
            x = rng.sample(range(52), 7)
            hole, board = tuple(x[:2]), tuple(x[2:2 + rng.choice((3, 4, 5))])
            st.append([list(hole), list(board), postflop_strength(hole, board), preflop_equity(hole)])
        hands = []
        for _ in range(300):
            d = list(range(52))
            rng.shuffle(d)
            a, b = Maniac(), CallStation()
            hands.append([d, play_hand((a, b), d, 10000, 50, 100).delta,
                          play_hand((b, a), d, 10000, 50, 100).delta])
        out = subprocess.run(["node", "-e", JS, str(WEB)], input=json.dumps({"ev": ev, "st": st, "hands": hands}),
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.stderr, "")
        self.assertEqual(out.stdout.strip(), "0")


if __name__ == "__main__":
    unittest.main()
