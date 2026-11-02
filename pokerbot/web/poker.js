// JavaScript port of the pokerbot engine + BasicBot, for the browser game (web/).
// Mirrors evaluator.py / engine.py / basic_bot.py. data = {preflop: {...}, params: {...}, original: {...}}
function createPoker(data) {
  const RANKS = "23456789TJQKA", SUITS = "cdhs";
  const FOLD = 0, CALL = 1, RAISE = 2;
  const BOARD_LEN = [0, 3, 4, 5];

  // ---------------- evaluator ----------------
  const STRAIGHT = new Int8Array(8192).fill(-1);
  for (let m = 0; m < 8192; m++) {
    for (let hi = 12; hi >= 4; hi--) {
      let ok = true;
      for (let k = 0; k < 5; k++) if (!((m >> (hi - k)) & 1)) { ok = false; break; }
      if (ok) { STRAIGHT[m] = hi; break; }
    }
    if (STRAIGHT[m] < 0 && (m & 0x100F) === 0x100F) STRAIGHT[m] = 3;
  }
  function top(mask, n) {
    let v = 0;
    for (let r = 12; r >= 0 && n > 0; r--) if ((mask >> r) & 1) { v = (v << 4) | r; n--; }
    return v;
  }
  function evaluate(cards) {
    const rc = new Array(13).fill(0), sc = [0, 0, 0, 0], sm = [0, 0, 0, 0];
    let mask = 0;
    for (const c of cards) {
      const r = c >> 2, s = c & 3;
      rc[r]++; sc[s]++; sm[s] |= 1 << r; mask |= 1 << r;
    }
    let fm = 0;
    for (let s = 0; s < 4; s++) if (sc[s] >= 5) { fm = sm[s]; break; }
    if (fm) { const sf = STRAIGHT[fm]; if (sf >= 0) return (8 << 20) | sf; }
    let quads = -1; const trips = [], pairs = [];
    for (let r = 12; r >= 0; r--) {
      const n = rc[r];
      if (n === 4) quads = r; else if (n === 3) trips.push(r); else if (n === 2) pairs.push(r);
    }
    if (quads >= 0) return (7 << 20) | (quads << 4) | top(mask & ~(1 << quads), 1);
    if (trips.length && (trips.length > 1 || pairs.length)) {
      return (6 << 20) | (trips[0] << 4) | Math.max(...trips.slice(1).concat(pairs));
    }
    if (fm) return (5 << 20) | top(fm, 5);
    const st = STRAIGHT[mask];
    if (st >= 0) return (4 << 20) | st;
    if (trips.length) return (3 << 20) | (trips[0] << 8) | top(mask & ~(1 << trips[0]), 2);
    if (pairs.length >= 2) {
      const p1 = pairs[0], p2 = pairs[1];
      return (2 << 20) | (p1 << 8) | (p2 << 4) | top(mask & ~(1 << p1) & ~(1 << p2), 1);
    }
    if (pairs.length) return (1 << 20) | (pairs[0] << 12) | top(mask & ~(1 << pairs[0]), 3);
    return top(mask, 5);
  }

  // ---------------- engine ----------------
  const act = (kind, amount = 0) => ({ kind, amount });
  const FOLD_A = act(FOLD), CALL_A = act(CALL);
  const raiseTo = (n) => act(RAISE, Math.trunc(n));

  // Generator: yields {cur, state, info} whenever a player must act; resume with next(action).
  // Returns {delta (for player 0 = button), showdown, hole, board, history}.
  function* playHand(deck, stack, sb, bb) {
    const hole = [[deck[0], deck[1]], [deck[2], deck[3]]];
    const fullBoard = deck.slice(4, 9);
    const stacks = [stack - sb, stack - bb], invested = [sb, bb];
    let bet = [sb, bb];
    const history = []; // [street, player, kind, added, streetTotal]
    let board = [];
    const finishFold = (loser) => ({
      delta: loser === 0 ? -invested[0] : invested[1], showdown: false, hole, board, history,
    });
    for (let street = 0; street < 4; street++) {
      board = fullBoard.slice(0, BOARD_LEN[street]);
      if (street) bet = [0, 0];
      if (stacks[0] > 0 && stacks[1] > 0) {
        let cur = street === 0 ? 0 : 1, lastRaise = bb;
        const acted = [false, false];
        while (!(acted[0] && acted[1] && bet[0] === bet[1])) {
          const o = 1 - cur;
          if (stacks[cur] === 0) { acted[cur] = true; cur = o; continue; }
          const toCall = bet[o] - bet[cur];
          const maxTo = Math.min(bet[cur] + stacks[cur], bet[o] + stacks[o]);
          const canRaise = maxTo > bet[o];
          const minTo = Math.min(bet[o] + lastRaise, maxTo);
          const state = {
            hole: hole[cur], board, street, pot: invested[0] + invested[1], toCall,
            myStack: stacks[cur], oppStack: stacks[o], myBet: bet[cur], oppBet: bet[o],
            minRaiseTo: minTo, maxRaiseTo: maxTo, canRaise, isButton: cur === 0, bigBlind: bb,
            history: history.map((h) => [h[0], h[1] === cur, h[2], h[3]]),
          };
          const info = { pot: invested[0] + invested[1], stacks: stacks.slice(), bets: bet.slice(), board, history };
          const a = yield { cur, state, info };
          let kind = a.kind;
          if (kind === FOLD) {
            if (toCall === 0) kind = CALL;
            else { history.push([street, cur, FOLD, 0, bet[cur]]); return finishFold(cur); }
          }
          if (kind === RAISE && !canRaise) kind = CALL;
          if (kind === CALL) {
            const add = Math.min(toCall, stacks[cur]);
            stacks[cur] -= add; bet[cur] += add; invested[cur] += add;
            history.push([street, cur, CALL, add, bet[cur]]);
          } else {
            const to = Math.max(minTo, Math.min(Math.trunc(a.amount), maxTo));
            const add = to - bet[cur];
            stacks[cur] -= add; bet[cur] = to; invested[cur] += add;
            lastRaise = Math.max(lastRaise, to - bet[o]);
            acted[o] = false;
            history.push([street, cur, RAISE, add, to]);
          }
          acted[cur] = true; cur = o;
        }
      }
    }
    const s0 = evaluate(hole[0].concat(fullBoard)), s1 = evaluate(hole[1].concat(fullBoard));
    const delta = s0 > s1 ? invested[1] : s0 < s1 ? -invested[0] : 0;
    return { delta, showdown: true, hole, board: fullBoard, history };
  }

  // ---------------- bots ----------------
  const ORIGINAL = data.original, TUNED = data.params;
  function clampRaise(s, amount) {
    if (!s.canRaise) return CALL_A;
    return raiseTo(Math.max(s.minRaiseTo, Math.min(Math.trunc(amount), s.maxRaiseTo)));
  }
  function preflopEquity(hole) {
    let a = hole[0] >> 2, b = hole[1] >> 2;
    if (a < b) [a, b] = [b, a];
    const key = a === b ? RANKS[a] + RANKS[a]
      : RANKS[a] + RANKS[b] + ((hole[0] & 3) === (hole[1] & 3) ? "s" : "o");
    return data.preflop[key];
  }
  function postflopStrength(hole, board) {
    const cards = hole.concat(board);
    const score = evaluate(cards), cat = score >> 20;
    const h0 = hole[0] >> 2, h1 = hole[1] >> 2, nb = board.length;
    const bmax = Math.max(...board.map((c) => c >> 2));
    let made = 0.2;
    if (nb === 5 && score === evaluate(board)) made = 0.3;
    else if (cat === 0) made = Math.max(h0, h1) === 12 ? 0.30 : Math.max(h0, h1) === 11 ? 0.26 : 0.2;
    else if (cat === 1) {
      const pr = (score >> 12) & 0xF;
      if (pr !== h0 && pr !== h1) made = 0.28;
      else if (h0 === h1) made = pr > bmax ? 0.75 : 0.5;
      else {
        const others = [...new Set(board.map((c) => c >> 2))].sort((x, y) => y - x);
        if (pr === others[0]) { const kick = pr === h0 ? h1 : h0; made = 0.62 + (kick >= 11 ? 0.05 : 0); }
        else if (others.length > 1 && pr === others[1]) made = 0.48;
        else made = 0.38;
      }
    } else if (cat === 2) {
      const p1 = (score >> 8) & 0xF, p2 = (score >> 4) & 0xF;
      const used = (p1 === h0 || p1 === h1 ? 1 : 0) + (p2 === h0 || p2 === h1 ? 1 : 0);
      made = [0.35, 0.68, 0.82][used];
    } else if (cat === 3) { const t = (score >> 8) & 0xF; made = t === h0 || t === h1 ? 0.88 : 0.4; }
    else if (cat === 4) made = 0.9;
    else if (cat === 5) made = 0.93;
    else if (cat === 6) made = 0.97;
    else made = 0.99;

    if (nb < 5 && cat < 4) {
      let outs = 0;
      for (let s = 0; s < 4; s++) {
        let n = 0, mine = false;
        for (const c of cards) if ((c & 3) === s) { n++; if (c === hole[0] || c === hole[1]) mine = true; }
        if (n === 4 && mine) outs += 9;
      }
      let bm = 0;
      for (const c of board) bm |= 1 << (c >> 2);
      const am = bm | (1 << h0) | (1 << h1);
      if (STRAIGHT[am] < 0) {
        let nOut = 0;
        for (let r = 0; r < 13; r++) {
          if (!((am >> r) & 1) && STRAIGHT[am | (1 << r)] >= 0 && STRAIGHT[bm | (1 << r)] < 0) nOut++;
        }
        outs += 4 * Math.min(nOut, 2);
      }
      if (outs) made = Math.max(made, Math.min(0.65, 0.06 + outs * (nb === 3 ? 0.04 : 0.022)));
    }
    return made;
  }

  class OpponentModel {
    constructor() {
      this.hands = 0; this.preOpenFaced = 0; this.preOpenFolds = 0;
      this.postBetsFaced = 0; this.postBetFolds = 0; this.postOppRaises = 0; this.postOppCalls = 0;
    }
    update(isButton, history) {
      const me = isButton ? 0 : 1;
      this.hands++;
      let curStreet = -1, lastRaiser = null, preRaises = 0;
      for (const [street, pl, kind] of history) {
        if (street !== curStreet) { curStreet = street; lastRaiser = null; }
        if (pl !== me) {
          if (street === 0) {
            if (lastRaiser === me && preRaises === 1) { this.preOpenFaced++; if (kind === FOLD) this.preOpenFolds++; }
          } else {
            if (lastRaiser === me) { this.postBetsFaced++; if (kind === FOLD) this.postBetFolds++; }
            if (kind === RAISE) this.postOppRaises++; else if (kind === CALL) this.postOppCalls++;
          }
        }
        if (kind === RAISE) { lastRaiser = pl; if (street === 0) preRaises++; }
      }
    }
    static rate(k, n, prior, w = 20) { return (k + prior * w) / (n + w); }
    get foldToBet() { return OpponentModel.rate(this.postBetFolds, this.postBetsFaced, 0.40); }
    get aggression() { return OpponentModel.rate(this.postOppRaises, this.postOppRaises + this.postOppCalls, 0.35); }
  }

  class BasicBot {
    constructor(params, adapt = true) {
      this.p = Object.assign({}, TUNED, params || {});
      this.adapt = adapt;               // true -> margin + value
      this.model = new OpponentModel();
    }
    onHandEnd(isButton, history) { if (this.adapt) this.model.update(isButton, history); }
    adj() {
      const m = this.model;
      if (!this.adapt || m.hands < 60) return [0, 0];
      const f = m.foldToBet;
      const margin = -0.06 * Math.max(-1, Math.min(1, (m.aggression - 0.35) / 0.3));
      const value = -0.06 * Math.max(0, Math.min(1, (0.35 - f) / 0.25));
      return [margin, value];
    }
    act(s) { return s.street === 0 ? this.preflop(s) : this.postflop(s); }
    preflop(s) {
      const p = this.p, [margin] = this.adj();
      const eq = preflopEquity(s.hole), bb = s.bigBlind, c = s.toCall, pot = s.pot;
      const nRaises = s.history.filter((h) => h[2] === RAISE).length, r = Math.random();
      if (nRaises === 0) {
        if (s.isButton) {
          if (eq >= p.open_eq) return clampRaise(s, p.open_size * bb);
          return eq >= p.limp_eq ? CALL_A : FOLD_A;
        }
        return eq >= p.iso_eq ? clampRaise(s, p.iso_size * bb) : CALL_A;
      }
      const odds = c ? c / (pot + c) : 0, pm = p.pre_margin + margin;
      if (nRaises === 1) {
        if (eq >= p.threebet_eq || (eq >= 0.50 && r < p.threebet_bluff)) return clampRaise(s, p.threebet_size * s.oppBet);
        return eq >= odds + pm ? CALL_A : FOLD_A;
      }
      if (eq >= p.fourbet_eq) {
        return clampRaise(s, s.oppBet > 0.2 * (s.myBet + s.myStack) ? s.maxRaiseTo : 2.3 * s.oppBet);
      }
      return eq >= odds + pm ? CALL_A : FOLD_A;
    }
    postflop(s) {
      const p = this.p, [margin, value] = this.adj();
      const st = postflopStrength(s.hole, s.board), pot = s.pot, c = s.toCall, r = Math.random();
      if (c === 0) {
        if (st >= p.value_eq + value) return clampRaise(s, p.value_size * pot);
        if (st >= p.med_eq + value) return r < p.med_freq ? clampRaise(s, p.med_size * pot) : CALL_A;
        if (st >= p.weak_eq) return r < p.weak_freq ? clampRaise(s, p.weak_size * pot) : CALL_A;
        return r < p.air_freq ? clampRaise(s, p.air_size * pot) : CALL_A;
      }
      const odds = c / (pot + c);
      if (st >= p.raise_eq || (st >= p.value_eq && r < p.raise_mid_freq)) return clampRaise(s, s.oppBet + p.raise_size * (pot + c));
      if (st >= odds + p.call_margin + margin) return CALL_A;
      if (r < p.bluff_raise_freq && c <= 0.5 * pot) return clampRaise(s, s.oppBet + p.raise_size * (pot + c));
      return FOLD_A;
    }
  }

  const TIGHT = { open_eq: 0.60, limp_eq: 0.50, iso_eq: 0.70, threebet_eq: 0.78, threebet_bluff: 0.0, pre_margin: 0.20,
    call_margin: 0.18, value_eq: 0.78, med_eq: 0.64, weak_freq: 0.08, air_freq: 0.02, bluff_raise_freq: 0.0 };
  const LOOSE = { open_eq: 0.42, limp_eq: 0.34, iso_eq: 0.50, threebet_eq: 0.62, threebet_bluff: 0.20, pre_margin: 0.06,
    call_margin: 0.03, value_eq: 0.62, med_eq: 0.45, weak_freq: 0.5, air_freq: 0.35, bluff_raise_freq: 0.15, raise_mid_freq: 0.6 };

  const BOT_FACTORIES = {
    basic: () => new BasicBot(null, true),
    basic0: () => new BasicBot(ORIGINAL, false),
    tight: () => new BasicBot(TIGHT, false),
    loose: () => new BasicBot(LOOSE, false),
    callstation: () => ({ act: () => CALL_A, onHandEnd() {} }),
    maniac: () => ({ act: (s) => (s.canRaise ? clampRaise(s, Math.min(s.oppBet + s.pot, s.maxRaiseTo)) : CALL_A), onHandEnd() {} }),
    random: () => ({
      act(s) {
        const r = Math.random();
        if (r < 0.15 && s.toCall) return FOLD_A;
        if (r < 0.35 && s.canRaise) return raiseTo(s.minRaiseTo + Math.floor(Math.random() * (s.maxRaiseTo - s.minRaiseTo + 1)));
        return CALL_A;
      }, onHandEnd() {},
    }),
  };

  function shuffledDeck(rng = Math.random) {
    const d = Array.from({ length: 52 }, (_, i) => i);
    for (let i = 51; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [d[i], d[j]] = [d[j], d[i]]; }
    return d;
  }
  function cardStr(c) { return RANKS[c >> 2] + SUITS[c & 3]; }

  return { evaluate, playHand, BOT_FACTORIES, BasicBot, shuffledDeck, cardStr, FOLD, CALL, RAISE, CALL_A, FOLD_A, raiseTo,
           postflopStrength, preflopEquity, STRAIGHT };
}
if (typeof module !== "undefined") module.exports = createPoker;
