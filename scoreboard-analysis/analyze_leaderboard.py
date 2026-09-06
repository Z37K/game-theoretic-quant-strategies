"""
Round 3 leaderboard analysis (18:30 snapshot, 24 Jun).
Goal: reverse-engineer how P&L / Sharpe percentile map to Final Score & rank,
so we can size capital/risk against target tiers (top 25 / 50 / 100).

Pure stdlib — no numpy/pandas needed.
"""
import csv, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "leaderboard_1830.csv")
START_EQUITY = 1_000_000

rows = []
with open(CSV, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({
            "rank": int(r["rank"]),
            "player": r["player"],
            "score": float(r["score"]),
            "pnl": float(r["pnl"]),
            "win": float(r["win_rate"]) if r["win_rate"] else None,
            "sharpe": float(r["sharpe"]),
        })

n = len(rows)

def pct_rank(vals, x):
    """Percentile (0-100): fraction of field with value <= x."""
    return 100.0 * sum(1 for v in vals if v <= x) / len(vals)

pnls = [r["pnl"] for r in rows]
sharpes = [r["sharpe"] for r in rows]
for r in rows:
    r["ret_pct"] = pct_rank(pnls, r["pnl"])
    r["shp_pct"] = pct_rank(sharpes, r["sharpe"])
    r["ret_%cap"] = 100.0 * r["pnl"] / START_EQUITY

# ---- 2-variable OLS: score ~ a + b*ret_pct + c*shp_pct ----
def ols2(y, x1, x2):
    m = len(y)
    s1 = sum(x1); s2 = sum(x2); sy = sum(y)
    s11 = sum(a*a for a in x1); s22 = sum(a*a for a in x2)
    s12 = sum(a*b for a,b in zip(x1,x2))
    s1y = sum(a*b for a,b in zip(x1,y)); s2y = sum(a*b for a,b in zip(x2,y))
    # normal equations  [m s1 s2; s1 s11 s12; s2 s12 s22] [a b c] = [sy s1y s2y]
    A = [[m,s1,s2],[s1,s11,s12],[s2,s12,s22]]
    rhs = [sy,s1y,s2y]
    # Gaussian elimination 3x3
    for i in range(3):
        p = A[i][i]
        for j in range(3): A[i][j] /= p
        rhs[i] /= p
        for k in range(3):
            if k!=i:
                f = A[k][i]
                for j in range(3): A[k][j] -= f*A[i][j]
                rhs[k] -= f*rhs[i]
    return rhs  # a,b,c

y  = [r["score"] for r in rows]
x1 = [r["ret_pct"] for r in rows]
x2 = [r["shp_pct"] for r in rows]
a,b,c = ols2(y,x1,x2)
pred = [a + b*p + c*q for p,q in zip(x1,x2)]
ybar = statistics.mean(y)
ss_tot = sum((v-ybar)**2 for v in y)
ss_res = sum((v-p)**2 for v,p in zip(y,pred))
r2 = 1 - ss_res/ss_tot

print("="*64)
print(f"FIELD: {n} players | snapshot 18:30, 24 Jun (Round 3)")
print("="*64)
print("\n--- OLS:  score ~ a + b*ReturnPct + c*SharpePct ---")
print(f"  intercept a = {a:6.2f}")
print(f"  ReturnPct b = {b:6.3f}   (Final-Score formula weight = 0.70)")
print(f"  SharpePct c = {c:6.3f}   (Final-Score formula weight = 0.10)")
print(f"  R^2         = {r2:6.3f}")
print("  (residual = the 0.15*DD + 0.05*RiskDiscipline we can't see directly)")

# ---- P&L thresholds by tier ----
print("\n--- WHAT P&L BUYS WHAT RANK (this field) ---")
print(f"{'tier':>10} | {'rank':>4} | {'P&L $':>12} | {'% of $1M':>8} | {'score':>6} | {'sharpe':>6}")
for tier in [1,5,10,25,50,71,100]:
    r = next(x for x in rows if x["rank"]==tier)
    print(f"{'#'+str(tier):>10} | {r['rank']:>4} | {r['pnl']:>12,.0f} | {r['ret_%cap']:>7.2f}% | {r['score']:>6.2f} | {r['sharpe']:>6.2f}")

# ---- positive-PnL cliff ----
pos = [r for r in rows if r["pnl"] > 0]
print(f"\n--- THE CLIFF ---")
print(f"  players with P&L > 0 : {len(pos)}  (worst is rank {max(r['rank'] for r in pos)})")
print(f"  => simply finishing non-negative ~= rank {max(r['rank'] for r in pos)}, safely in Top-100")

# ---- marginal value of return at the top vs middle ----
# Picked by position, not by name: the biggest earner in the field vs whoever
# actually holds rank 1. They are not the same person, and that is the point.
print("\n--- RETURN PERCENTILE IS SATURATING AT THE TOP ---")
big = max(rows, key=lambda r: r["pnl"])          # largest P&L in the field
top = next(r for r in rows if r["rank"] == 1)    # actual rank 1
print(f"  biggest P&L : {big['player']:>10}  P&L {big['pnl']:>10,.0f} ({big['ret_%cap']:.1f}%)  retPct {big['ret_pct']:.0f}  sharpe {big['sharpe']}  -> rank {big['rank']}")
print(f"  rank 1      : {top['player']:>10}  P&L {top['pnl']:>10,.0f} ({top['ret_%cap']:.1f}%)  retPct {top['ret_pct']:.0f}  sharpe {top['sharpe']}  -> rank {top['rank']}")
print(f"  The biggest earner made {big['pnl']/top['pnl']:.1f}x the P&L of rank 1 and still ranks BELOW them.")
print(f"  Implied: above ~the top decile of P&L, extra return adds ~{b*(big['ret_pct']-top['ret_pct']):.1f} score pts;")
print(f"           the rank-1 sharpe edge alone is worth ~{c*(top['shp_pct']-big['shp_pct']):.1f} pts + DD/Risk residual.")

# ---- me ----
me = next(r for r in rows if r["player"] == "me")
print(f"\n--- ME ---")
print(f"  rank {me['rank']} | score {me['score']} | P&L {me['pnl']:,.0f} ({me['ret_%cap']:.3f}%) | retPct {me['ret_pct']:.0f} | sharpe {me['sharpe']} (shpPct {me['shp_pct']:.0f})")
gap25 = next(r for r in rows if r["rank"]==25)
gap10 = next(r for r in rows if r["rank"]==10)
print(f"  to reach top-25: need score >= {gap25['score']} (currently {me['score']}, gap {gap25['score']-me['score']:.2f})")
print(f"     ~ P&L around {gap25['pnl']:,.0f} ({gap25['ret_%cap']:.1f}% of capital) at comparable smoothness")
print(f"  to reach top-10: need score >= {gap10['score']}  ~ P&L {gap10['pnl']:,.0f} ({gap10['ret_%cap']:.1f}%)")
print("="*64)
