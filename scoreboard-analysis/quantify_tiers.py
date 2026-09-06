"""
Quantify: what P&L / Sharpe / combination buys what rank.
Uses leaderboard_1830.csv (18:30 snapshot, 101 players).
Builds empirical crosstabs + inverts the fitted score model into a
target-rank -> required-P&L lookup at chosen Sharpe levels.
"""
import csv, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
with open(os.path.join(HERE, "leaderboard_1830.csv"), newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({"rank": int(r["rank"]), "score": float(r["score"]),
                     "pnl": float(r["pnl"]), "sharpe": float(r["sharpe"])})
n = len(rows)
pnls_sorted = sorted(r["pnl"] for r in rows)
shp_sorted  = sorted(r["sharpe"] for r in rows)

def band_report(rows, key, bands, labels):
    print(f"\n{'band':>16} | {'n':>3} | {'best':>4} | {'med':>4} | {'worst':>5} | {'med score':>9}")
    print("-"*58)
    for (lo,hi),lab in zip(bands,labels):
        g = [r for r in rows if lo <= r[key] < hi]
        if not g:
            print(f"{lab:>16} |   0 |    - |    - |     - |         -"); continue
        rk = sorted(x["rank"] for x in g)
        sc = statistics.median(x["score"] for x in g)
        print(f"{lab:>16} | {len(g):>3} | {rk[0]:>4} | {rk[len(rk)//2]:>4} | {rk[-1]:>5} | {sc:>9.1f}")

print("="*70)
print("A) WHAT P&L BUYS WHAT RANK")
band_report(rows, "pnl",
    [(-1e9,0),(0,1000),(1000,10000),(10000,100000),(100000,1e9)],
    ["negative","$0-1k (3 fig)","$1k-10k (4 fig)","$10k-100k (5 fig)","$100k+ (6 fig)"])

print("\n"+"="*70)
print("B) WHAT SHARPE BUYS WHAT RANK")
band_report(rows, "sharpe",
    [(-1e9,0),(0,0.05),(0.05,0.10),(0.10,0.20),(0.20,1e9)],
    ["negative","0.00-0.05","0.05-0.10","0.10-0.20","0.20+"])

print("\n"+"="*70)
print("C) 2D GRID: median rank by  P&L band (rows) x Sharpe band (cols)")
pnl_bands = [(-1e9,0),(0,10000),(10000,100000),(100000,1e9)]
pnl_lab   = ["neg","$0-10k","$10-100k","$100k+"]
shp_bands = [(-1e9,0),(0,0.10),(0.10,1e9)]
shp_lab   = ["shp<0","shp0-.10","shp.10+"]
print(f"{'':>10} | " + " | ".join(f"{l:>9}" for l in shp_lab))
print("-"*46)
for (plo,phi),pl in zip(pnl_bands,pnl_lab):
    cells=[]
    for (slo,shi) in shp_bands:
        g=[r for r in rows if plo<=r["pnl"]<phi and slo<=r["sharpe"]<shi]
        cells.append(f"{statistics.median(x['rank'] for x in g):>9.0f}" if g else f"{'-':>9}")
    print(f"{pl:>10} | " + " | ".join(cells))

# ---- inverse percentile helpers ----
def value_at_pct(sorted_vals, pct):
    """value at given percentile (0-100)"""
    if pct<=0: return sorted_vals[0]
    if pct>=100: return sorted_vals[-1]
    i = pct/100*(len(sorted_vals)-1)
    lo=int(i); frac=i-lo
    return sorted_vals[lo]+frac*(sorted_vals[min(lo+1,len(sorted_vals)-1)]-sorted_vals[lo])
def pct_of_value(sorted_vals, x):
    return 100.0*sum(1 for v in sorted_vals if v<=x)/len(sorted_vals)

# fitted model (from analyze_leaderboard.py): score = a + b*RetPct + c*ShpPct
a,b,c = 19.99, 0.690, 0.085

def score_to_rank(s):
    return sum(1 for r in rows if r["score"]>s)+1

print("\n"+"="*70)
print("D) TARGET RANK  ->  REQUIRED P&L, at a chosen Sharpe")
print("   (assumes a clean book: full Drawdown+Risk credit, baked into model)")
targets = [3,5,10,15,25,40]
sharpe_scen = [0.00, 0.10, 0.20, 0.50, 0.88]
# score needed for each target rank = score of the player currently at that rank
print(f"\n{'rank':>5} | {'score':>6} || " + " | ".join(f"shp={s:<4}" for s in sharpe_scen))
print("-"*70)
for t in targets:
    s_needed = next(r["score"] for r in rows if r["rank"]==t)
    cells=[]
    for shp in sharpe_scen:
        shp_pct = pct_of_value(shp_sorted, shp)
        ret_pct = (s_needed - a - c*shp_pct)/b
        if ret_pct>100: cells.append("  >100pc")
        elif ret_pct<0: cells.append("   $0-ish")
        else:
            pnl = value_at_pct(pnls_sorted, ret_pct)
            cells.append(f"{pnl:>8,.0f}")
    print(f"{t:>5} | {s_needed:>6.1f} || " + " | ".join(cells))

print("\n  (read: to reach rank R at Sharpe S, you need ~that P&L. Higher Sharpe")
print("   lowers the P&L bar — the smooth-equity route.)")

print("\n"+"="*70)
print("E) SCORE -> RANK ladder")
for s in [88,86,84,82,80,77,73,67,55,34]:
    print(f"   score {s:>3}  ->  about rank {score_to_rank(s):>3}")
print("="*70)
