"""
barrier_score_test.py - the HONEST version: score the flatten-at-target ladder on the
FULL competition formula, not just return-rank.

For each 48h window we simulate the adaptive ladder (T_hi=12% -> T_lo=4% last 8h, -40%
self-stop, edge direction), and measure the realised equity path's:
  - return        -> ReturnRank   (leaderboard P&L percentile)
  - MaxDrawdown   -> DrawdownRank  (ASSUMED decay curve; we lack peers' DD)
  - 15-min Sharpe -> SharpeRank    (leaderboard Sharpe percentile; cap 50 if <8 obs)
  - Risk = 80     (single-instrument directional trips concentration penalties)
Score = 0.70*Ret + 0.15*DD + 0.10*Shp + 0.05*Risk ; map E[Score] -> expected rank.
Contrast with the return-ONLY view to show the 30%-bucket drag.

Pure stdlib.
"""
import os, csv, statistics, math

HERE=os.path.dirname(os.path.abspath(__file__)); DATA=os.path.join(HERE,"crypto-data")
SYMS=["BTCUSD","ETHUSD","SOLUSD"]; WLEN=2880; STEP=360; BTC_TREND=720
T_HI=0.12; T_LO=0.04; LATE_BARS=8*60; SELF_STOP=-0.40; RISK=80
LB=list(csv.DictReader(open(os.path.join(HERE,"..","scoreboard-analysis","leaderboard_1830.csv"),encoding="utf-8")))
_pnls=sorted(float(r["pnl"]) for r in LB); _shps=sorted(float(r["sharpe"]) for r in LB); _scores=sorted(float(r["score"]) for r in LB)
def ret_pct(r): return 100.0*sum(1 for v in _pnls if v<=r*1_000_000)/len(_pnls)
def shp_pct(s): return 100.0*sum(1 for v in _shps if v<=s)/len(_shps)
def dd_pct(d): return min(97.0,95.0*math.exp(-d*100/15.0))   # d as fraction
def score_to_rank(s): return sum(1 for r in LB if float(r["score"])>s)+1

def load(sym):
    p=os.path.join(DATA,f"{sym}_1m.csv"); H=[];L=[];C=[]
    with open(p) as f:
        rd=csv.reader(f); next(rd,None)
        for row in rd:
            try: H.append(float(row[2]));L.append(float(row[3]));C.append(float(row[4]))
            except (ValueError,IndexError): pass
    return H,L,C

def sim(H,L,C,s,lev,direction):
    """Return (final_ret, maxdd, sharpe). Equity held flat after flatten."""
    entry=C[s]; r_hard=0.01-1.0/lev; end=min(s+WLEN,len(C)); switch=end-LATE_BARS
    eq_samples=[1.0]; locked=None; peak=1.0; mdd=0.0; eq=1.0
    for i in range(s+1,end):
        if locked is None:
            if direction>0: worst=L[i]/entry-1; best=H[i]/entry-1
            else:           worst=1-H[i]/entry; best=1-L[i]/entry
            if worst<=r_hard:           locked=1+lev*r_hard          # hard DQ (~ -0.9)
            elif (1+lev*worst)<=1+SELF_STOP: locked=1+SELF_STOP      # self-stop
            else:
                tgt=T_HI if i<switch else T_LO
                if 1+lev*best>=1+tgt: locked=1+tgt                   # win
            eq = locked if locked is not None else 1+lev*(C[i]/entry-1 if direction>0 else 1-C[i]/entry)
        else:
            eq = locked
        peak=max(peak,eq); mdd=max(mdd,(peak-eq)/peak if peak>0 else 0)
        if (i-s)%15==0: eq_samples.append(eq)
    final=(eq-1.0)
    rets=[eq_samples[k]/eq_samples[k-1]-1 for k in range(1,len(eq_samples)) if eq_samples[k-1]>0]
    if len(rets)>=8 and statistics.pstdev(rets)>0:
        shp=statistics.mean(rets)/statistics.pstdev(rets); shp_capped=False
    else:
        shp=0.0; shp_capped=True
    return final, mdd, shp, shp_capped

def main():
    btcC=load("BTCUSD")[2]
    print("Adaptive ladder, edge direction. FULL score vs return-only.\n")
    print(f"{'coin':>6} {'lev':>3} | {'E[Ret%]':>7} {'E[DD%]':>6} {'E[Shp]':>6} | {'E[RetRank]':>10} {'E[Score]':>8} | {'rank(full)':>10} {'rank(ret-only)':>13}")
    print("-"*94)
    for sym in SYMS:
        H,L,C=load(sym); n=min(len(C),len(btcC)); starts=list(range(BTC_TREND,n-WLEN,STEP))
        for lev in (5,8):
            scores=[]; retranks=[]; rets=[]; dds=[]; shps=[]
            for s in starts:
                d=1 if btcC[s]>btcC[s-BTC_TREND] else -1
                fr,mdd,shp,cap=sim(H,L,C,s,lev,d)
                rr=ret_pct(fr); dr=dd_pct(mdd); sr=min(50.0,shp_pct(shp)) if cap else shp_pct(shp)
                sc=0.70*rr+0.15*dr+0.10*sr+0.05*RISK
                scores.append(sc); retranks.append(rr); rets.append(fr*100); dds.append(mdd*100); shps.append(shp)
            eS=statistics.mean(scores); eRR=statistics.mean(retranks)
            # expected rank from full score vs from return-only (treat retrank as a pseudo-score on same scale? no:
            # ret-only "rank" = rank if score were 0.70*RetRank + full DD/Shp/Risk assumed perfect (clean-book illusion))
            ret_only_score=0.70*eRR+0.15*97+0.10*shp_pct(0.2)+0.05*100  # the optimistic clean-book framing
            print(f"{sym:>6} {lev:>3} | {statistics.mean(rets):7.1f} {statistics.mean(dds):6.1f} {statistics.mean(shps):6.3f} | "
                  f"{eRR:10.1f} {eS:8.1f} | {score_to_rank(eS):10d} {score_to_rank(ret_only_score):13d}")
        print()
    print("rank(full) = expected rank incl. measured DD/Sharpe (the 30%).")
    print("rank(ret-only) = the optimistic framing that assumed a clean book (DD~0, Shp~0.2).")
    print("Risk fixed at 80 (single-instrument concentration). DDRank uses the assumed decay curve.")

if __name__=="__main__":
    main()
