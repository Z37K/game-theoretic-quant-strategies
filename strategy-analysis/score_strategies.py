"""
Objective strategy scorecard.
E[FinalScore] = (1 - P_elim) * [0.70*RetPct + 0.10*ShpPct + 0.15*DDpct + 0.05*RiskDisc]

Inputs per strategy are ESTIMATES (priors). RetPct given as (lo,hi) range;
midpoint used for the headline E[score], range shown alongside.
ShpPct: empirical, from the snapshot Sharpe distribution.
DDpct : documented decay map (peers' drawdowns are unobserved -> assumption).
Complexity = count of moving parts to manage (NOT in the formula; tiebreaker).
"""
import csv, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
shp_field = sorted(float(r["sharpe"]) for r in
                   csv.DictReader(open(os.path.join(HERE,"..","scoreboard-analysis","leaderboard_1830.csv"),encoding="utf-8")))

def shp_pct(s):                       # empirical percentile of a Sharpe value
    return 100.0*sum(1 for v in shp_field if v<=s)/len(shp_field)

def dd_pct(maxdd):                    # ASSUMPTION: clean book ~ rare/top; decay with DD%
    return min(97.0, 95.0*math.exp(-maxdd/15.0))

W = dict(ret=0.70, shp=0.10, dd=0.15, risk=0.05)

# strat = (name, RetLo, RetHi, Shp, MaxDD%, P_elim, RiskDisc, complexity, DirEdge, SnapCtrl, Legal, tag)
# v2 inputs: corrected after sense-check (see chat). Return now requires a real
# source (edge/carry/crypto-vol); smoothness only buys the 30%, not the 70%.
S = [
 # NOTE: these 'static' rows = NO optional-stopping baseline (coin-flip lottery).
 # SUPERSEDED for decision-making by barrier_test.py (flatten-at-target): 5x+flatten@+4%
 # ~= 82% chance of Top-25 for ~0.3% elim. Linear E below understates that, so don't
 # rank crypto off these rows -- use the barrier model.
 ("Crypto static 5x (baseline, no-flatten)",20,92,0.00,25,0.01,80,3,0,1,1,"coin-flip; see barrier_test"),
 ("Crypto static 8x (baseline, no-flatten)",25,96,0.01,35,0.04,80,3,0,1,1,"coin-flip; see barrier_test"),
 ("Mean-reversion (FX+metals)",38,70,0.13,12,0.10,85,6,1,1,1,"better intraday prior; trend-day tail"),
 ("Cross-asset RV (EUR complex, XAU/XAG)",35,58,0.12,6,0.06,95,8,1,1,1,"netting limits; smoother"),
 ("Trend / momentum (FX+metals)",35,72,0.07,8,0.06,90,6,1,1,1,"weak intraday prior; metals>FX"),
 ("Breakout / session open",35,70,0.06,9,0.06,90,6,1,1,1,"false-break bleed"),
 ("Round-boundary risk timing (modifier on a bet)",40,78,0.05,3,0.12,90,5,1,1,1,"DD resets; not a return source itself"),
 ("Smooth Sharpe + small edge (rank-1 style)",35,48,0.20,1.5,0.03,100,4,1,1,1,"needs a return engine; not edge-free"),
 ("Flat/near-flat metric book (current posture)",30,40,0.09,0.5,0.01,100,2,0,1,1,"validates @ rank44 (the floor)"),
 ("Vol harvesting / grid",33,58,0.08,15,0.13,85,6,0,1,1,"trend-day tail"),
 ("Carry / overnight drift",28,40,0.06,6,0.06,90,4,1,1,1,"negligible over 2-day finals"),
 ("Inventory-flat churn (trade-count/Sharpe farm)",25,35,0.04,2,0.02,100,5,0,1,1,"net-NEG after spread; $10k-elig only"),
 ("Passive MM / spread capture (taker base case)",28,42,0.05,5,0.05,100,8,0,1,1,"premise likely FALSE; 82 only IF resting fills"),
 ("Brute-force max-leverage push (Finals only)",60,98,0.03,30,0.35,80,4,1,1,1,"zeroes you if it fails"),
]

rows=[]
for (nm,rlo,rhi,shp,dd,pe,risk,cx,de,sc,lg,tag) in S:
    sp, dp = shp_pct(shp), dd_pct(dd)
    def score(rp): return (1-pe)*(W["ret"]*rp + W["shp"]*sp + W["dd"]*dp + W["risk"]*risk)
    e_lo,e_hi = score(rlo),score(rhi); e_mid=score((rlo+rhi)/2)
    rows.append((e_mid,e_lo,e_hi,nm,rlo,rhi,shp,sp,dd,dp,pe,risk,cx,de,sc,lg,tag))

# --- calibration: anchor raw E[score] so the flat-book posture == its observed 73.23 ---
flat_raw = next(r[0] for r in rows if r[3].startswith("Flat/near-flat"))
OFFSET = 73.23 - flat_raw   # ~ +22.5 ; corrects the clean-book residual uniformly (approx)

rows.sort(reverse=True)
print("="*124)
print(f"{'STRATEGY':<46}{'Cal':>6}{'E[raw]':>8}{'(range)':>11}  {'Ret%':>7} {'Shp':>5} {'ShpP':>5} {'DD%':>5} {'DDp':>4} {'Pelim':>6} {'cx':>3} {'edge':>5} {'snap':>5}")
print("-"*124)
for (em,el,eh,nm,rlo,rhi,shp,sp,dd,dp,pe,risk,cx,de,sc,lg,tag) in rows:
    cal=em+OFFSET
    print(f"{nm:<46}{cal:>6.1f}{em:>8.1f}{f'[{el:.0f}-{eh:.0f}]':>11}  {f'{rlo:.0f}-{rhi:.0f}':>7} {shp:>5.2f} {sp:>5.0f} {dd:>5.1f} {dp:>4.0f} {pe:>6.2f} {cx:>3} {('Y' if de else 'N'):>5} {('Y' if sc else 'N'):>5}")
print("="*124)
print(f"Cal = E[raw] + {OFFSET:.1f} (offset anchored to flat-book observed 73.23). Cal ~ real leaderboard scale.")
print("\nNotes:")
for (em,el,eh,nm,rlo,rhi,shp,sp,dd,dp,pe,risk,cx,de,sc,lg,tag) in rows:
    if tag: print(f"  - {nm.split('(')[0].strip()}: {tag}")
print("\nReminders: E[Score] uses RetPct midpoint. DirEdge=Y rows have the WIDE Ret range")
print("(load-bearing on us being right). DDpct is an assumed decay curve, not measured.")
print("For reference our model put score~73 at the flat-book posture -> sanity check below.")
