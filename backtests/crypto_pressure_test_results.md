# Crypto Pressure-Test Results

Measured on 1yr of Binance 1m bars (crypto-data/), competition mechanics modelled
(fixed-notional, 30%-margin stop-out, 2bps/flip cost). Script: crypto_pressure_test.py.
Validated: Binance prices ≈ live Syphonix feed (BTC 60.9k, ETH 1617, SOL 67.9, XRP 1.07).

## Headline findings
1. **Momentum/trend-follow is DEAD.** Negative median return AND negative Sharpe at
   every leverage, every coin. Catastrophic on BAR (mom p50 = −25% to −100%). Do not
   trend-follow crypto on intraday bars.
2. **Static directional = a tunable LOTTERY, not a path.** Median return ≈0 (a random
   crypto window is ~flat), so RetPct@p50 is mediocre (~5–50). All the Top-10 value is
   in the p90 tail → luck, unless we add real directional edge.
3. **Sharpe ≈ 0** for static crypto → does nothing for the 10% term or the $10k award.
4. **P_elim scales with coin vol & leverage**; BTC safest, BAR/SOL hottest (7% daily vol).
5. **High median at 20–30x is survivorship bias** — the eliminated windows are dropped
   from the percentiles; true EV includes the (large) elimination probability.

## P_elim by leverage — static, 48h (finals window)
| lev | BTC | ETH | SOL | XRP | BAR | p90 RetPct (Top-10 shot) |
|---|---|---|---|---|---|---|
| 2x | 0% | 0% | 0% | ~0% | 0% | 83–89 |
| **5x** | 0.1% | 0.8% | 1.2% | ~1% | 1.2% | **91–95** |
| 8x | 1.4% | 3.7% | 4.6% | 3.3% | 2.3% | 93–98 |
| 12x | 5.8% | 13.3% | 17.7% | 13.4% | 7.8% | 98–100 |
| 20x | 20% | 37% | 41% | 36% | 32% | 100 |
| 30x | 40% | 54% | 62% | 59% | 54% | 100 |

## Lottery-ticket pricing (static, 48h)
- **5x:** pay ~1% elimination risk → ~10% chance of landing RetPct 91–95 (Top 5–10),
  ~50% chance mediocre, downside p10 −20% to −33%. Best risk/reward for the upside.
- **8x:** ~2–5% elim → p90 RetPct 93–98. More upside, still modest elim.
- **≥12x:** elim cost (6–60%) not worth it. 20–30x is Russian roulette.
- **Tunable:** deploy only fraction f of capital → effective leverage f×L; dials the
  ticket size and cuts elim further.

## Implication for the scorecard
Crypto's old guess (Ret 50–96, P_elim 0.22, Shp 0.06) was wrong both ways: **safer**
at low leverage (P_elim ~0.01 at 5x) but **lower/again tail-driven** median and **~0
Sharpe**. It's not a reliable Top-10 route — it's a cheap, controllable variance
instrument: convert a guaranteed mid-tier into a ~10% shot at Top-10 for ~1% elim cost.
Rational ONLY if we want a prize tier we can't otherwise reach AND can afford the small
chance of losing our safe finalist slot (which also forfeits $10k-Sharpe eligibility).

---

## UPDATE: flatten-at-target changes the conclusion (barrier_test.py)

Modelling the optional-stopping rule (flatten the instant equity touches +T; eliminated
only if the 30%-margin stop hits first) as a DOUBLE-BARRIER first-passage problem turns
crypto from a coin-flip lottery (E[RetPct]~37) into a high-probability tier-jump.

Why: at leverage L a +T equity target = only +T/L price move, while stop-out = ~1/L
price against. The barriers are wildly asymmetric in our favour; 48h of vol touches the
small upside barrier far more often than the big downside one.

Frontier (edge-direction, avg BTC/ETH/SOL/XRP):
| target | locks RetRank | ~rank | P(hit) 5x/8x | P(elim) 5x/8x |
|---|---|---|---|---|
| +2% | 71 | ~29 | 91/94% | 0.2/0.9% |
| +4% | 77 | ~23 | 82/89% | 0.25/1.0% |
| +7% | 84 | ~16 | 70/81% | 0.35/1.3% |
| +12% | 89 | ~11 | 53/68% | 0.45/1.8% |
| +20% | 92 | ~8 | 34/50% | 0.4/2.7% |

Conclusion: **5x + flatten@+4% ≈ 82% chance of Top-25 for ~0.3% elim** — dominates the
whole strategy menu for the Top-25 goal. Engine = leverage + optional stopping (NOT the
edge; 'edge' barely beats 'long'). Execution: adaptive ladder — enter ~6-8x, target +12%
(Top-10), ratchet to +4% (Top-25) if untriggered with ~8h left.
Caveats: blinded-finals field shift, gap/slippage past stop, single 48h draw, ~1-2%
elimination = DQ.

### Robustness (robustness_test.py)
- Adaptive ladder (hold +12% Top-10, ratchet to +4% Top-25 in last 8h): SOL 8x gives
  ~74% Top-10 / 4% Top-25 floor / 19% hold / 2.8% DQ. BTC 8x = safest (0.4% DQ) but
  only 53% Top-10. ~20-47% "hold" bucket can land BELOW Top-25 = the ladder's risk.
- Self-imposed stop: a −40%-equity self-stop kills hard-DQ (2.3%→0%) for ~1pt E[RetPct].
  −19% is too tight (33% stopped on noise). Recommend ~−40% at 8x.
- Coin: BTC safest/low-upside; SOL highest upside/highest DQ; ETH/XRP middle.
- Two clean configs:
  - FLOOR-FIRST (reliable Top-25): fixed flatten @+4%, 5x -> ~83% Top-25, ~0.3% DQ.
  - UPSIDE-FIRST (reach Top-10): ladder, 8x + −40% self-stop, SOL/ETH -> ~70% Top-10,
    0% DQ, ~20% below Top-25.
- Sharpe: this play gives Sharpe ~0.07 (single jump). 0.2/0.88 milestones NOT addressed
  by it; grid/ping-pong (grid_backtest.py) is the untested high-Sharpe candidate.
