# Strategy Menu — full brainstorm (from to_optimise.md only)

Generated before narrowing. Captures every category of lever, trading + metagame.

## Framing anchors (drive everything below)
- **70% is Return, cumulative, never rebased.** Outweighs the other three combined (15+10+5=30). Game is mostly "out-return peers over the whole competition."
- **Ranks are percentile vs. active peers** → don't need a number, need to beat people. Peer behavior + peer blowups are part of the alpha.
- **Drawdown & Risk-Discipline reset each round; Return doesn't.** Intra-round risk is "forgiven" at each 22:00 snapshot — *unless mid-drawdown at the snapshot itself.* Dangerous instant = the cutoff, not volatility generally.
- **Stop-out at 30% margin = elimination**, zeroes the permanent Return. Only truly irreversible failure.
- **Finals blinded** — after 24 Jun 22:00 no peer visibility, so any "match the leader" tactic must execute *before* Finals.

---

## A. Directional alpha (earn return by predicting price)
| Approach | Core mechanism | What must be true | Biggest risk given constraints |
|---|---|---|---|
| Trend / momentum | Ride autocorrelated moves; add on confirmation | FX/metals show persistent intraday trends in round window | Whipsaw; at 30x a reversal can hit 30% stop-out → elimination |
| Mean-reversion | Fade stretched moves to band/VWAP | Ranging regime; bounded excursions | Trending day = unbounded loss; netting blocks same-symbol hedge |
| Breakout / vol expansion | Enter on range breaks, session opens | Real follow-through | False breaks bleed; modeled spread+slippage taxes re-entry |
| Cross-asset / RV | Trade correlated pairs (EUR complex, XAU/XAG, USD legs) | Stable correlation; one leg leads | Netting+15 symbols limits true pairs; doubles margin |
| Carry / overnight drift | Hold positive-carry FX direction | Carry sign stable over round | Tiny edge vs 24h; needs leverage → Risk-Discipline lines |
| Crypto directional (live only) | Trade BTC/ETH/SOL/XRP/BAR for higher vol | Crypto vol = bigger Return upside | **Zero backtest data**; highest blowup/elimination risk |

## B. No-edge / microstructure / market-making
| Approach | Core mechanism | What must be true | Biggest risk |
|---|---|---|---|
| Spread capture / passive MM | Quote both sides, earn bid/ask | Actually get passive fills | Sim crosses spread every entry/exit — if no resting orders, you *pay* spread. Verify fill model |
| Inventory-flat scalping | Many tiny round-trips, stay flat | Edge per trade > modeled cost | Slippage/impact → churn net-negative; only farms ≥30-trade count |
| Round-number LP | Lean on FX figure levels | Quotes rest and get hit | Same fill-model dependency; netting collapses two-sided inventory |
| Vol harvesting (gamma-style) | Buy dips/sell rips in a band | Realized range > costs | Mean-reversion in disguise → trend-day tail risk |

## C. Rank / tournament-theory (rational *because* scoring is relative)
| Approach | Core mechanism | What must be true | Biggest risk |
|---|---|---|---|
| Variance-matching to rank | Leading → cut variance to lock; trailing → add variance to gamble up | Can see rank (true R1–3, **blind Finals**) | Misjudge field; blind Finals kills live version |
| Satisfice to cutoff | Only need Top 100 at R3 — clear the bar | Reliable read on 100th-place line | Cutoff is moving target; cutting close risks noise miss |
| Round-boundary risk timing | DD/Risk reset, Return persists → take risk into round, be flat at 22:00 | Can flatten at snapshot reliably | Gap/slippage flattening; over-optimizing the instant |
| Survival / last-man-standing | Peers self-eliminate via stop-out; not blowing up drifts percentile up | Enough peers take elimination risk | Passive — disciplined field → mediocre Return rank |
| Snapshot drawdown mgmt | DD only cares about trough in-round at cutoff — repair before 22:00 | DD measured to snapshot, recoverable | Underwater at 22:00 = full DD; netting limits fast neutralize |
| Finals regime switch | Pre-Finals play relative w/ peer info; Finals switch to absolute/survival | Pre-Finals standing bankable | Finals Return still cumulative & relative; blind = optimize in dark |
| Cutoff-clustering / herd-fade | Trade flow from peers de-risking/gambling at 22:00 | Peer behavior predictable & moves price | Speculative; depends on unobservable field |

## D. Pure metric-engineering (target a component directly)
| Target | Mechanism | What must be true | Biggest risk |
|---|---|---|---|
| Drawdown rank (15%) | Run near-flat so trough is microscopic | Low activity yields valid round | Costs Return (70%); great DD + weak Return loses |
| Sharpe rank (10%) | Smooth low-vol curve; ≥8 valid 15-min obs or capped at 50 | ≥2h sampled equity change/round | Smoothness ↔ return tension; need *some* positive drift |
| Sharpe-obs farming | Small periodic equity changes every 15 min | Sampling time-based; trivial trades count | Over-trading adds cost; gaming count ≠ better ratio |
| Risk-Discipline (5%) | Stay under all margin/lev/concentration lines | Know thresholds (we do) | Cheapest to max, smallest weight; the leverage that trips it also stops you out |
| $10k Sharpe Award | Competition-wide Sharpe + ≥30 trades + Top 50 + zero red-line | Already Top 50 & finals-qual | Different objective (comp-wide) — conflicts w/ per-round aggression |
| Best Tech Architecture $10k | P&L-independent; system/AI design + demo | Submit repo + demo after R3 | Pure effort cost, zero P&L coupling |
| Elimination-avoidance | Treat "not stopped out" as master constraint | Margin never near 30% | Only irreversible mistake; size everything against it |

## Cross-cutting tensions
- **Leverage is double-edged:** how you win Return rank *and* how you get eliminated / trip Risk-Discipline. Most of the menu = "how much of 30x, and when."
- **Netting + 15 symbols** kills classic market-neutral & same-symbol pairs; RV must be cross-symbol, costs double margin.
- **No crypto backtest data** splits universe into validated (FX/metals) vs live-only gamble (5 cryptos) — crypto holds the outsized Return-rank upside.
- **Snapshot, not session, is scored** for DD/Risk — much of metric-engineering collapses to "what does my account look like at exactly 22:00."
