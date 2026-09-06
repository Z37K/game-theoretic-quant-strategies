"""
crypto_pressure_test.py - measure the REAL return distribution and P_elim of
directional crypto trading under competition mechanics, to replace the guessed
scorecard inputs (Ret 50-96, P_elim 0.22).

Mechanics modelled:
  - Fixed-notional position: open N = L * equity_at_entry, hold until flip/close.
  - Stop-out (= ELIMINATION) when margin level <= 30%, i.e. the position's
    return on equity p_ret <= r_stop = 0.01 - 1/L  (intrabar high/low checked).
  - Spread cost COST_BPS charged on every flip (taker).
  - Rounds are 24h or 48h windows; we roll the start across ~1 year of 1m bars
    to sample bull / bear / chop regimes.

Strategies: 'static' (hold long, ride drift) and 'mom' (trend-follow a lookback).
Output per symbol: leverage sweep -> P_elim, surviving-return p10/50/90, Sharpe,
and the leaderboard ReturnPct those returns map to.

Pure stdlib.
"""
import os, csv, statistics, math

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "crypto-data")
SYMS = ["BTCUSD","ETHUSD","SOLUSD","XRPUSD","BARUSD"]

COST_BPS    = 2.0        # round-trip per flip (taker). Observed live Syphonix spreads:
                         # XRP 1.1bps, XAG 2.5bps, BTC/ETH/SOL ~1-3bps (inst-tight).
LEVS        = [2,3,5,8,12,20,30]
WINDOWS     = {"24h":1440, "48h":2880}
STEP        = 360        # roll start every 6h
MOM_LOOKBACK= 120        # 2h momentum lookback for the 'mom' strategy

# ---- leaderboard ReturnPct mapping (P&L on $1M -> percentile) ----
_pnls = sorted(float(r["pnl"]) for r in
               csv.DictReader(open(os.path.join(HERE,"..","scoreboard-analysis","leaderboard_1830.csv"),encoding="utf-8")))
def ret_to_pct(ret_frac):
    pnl = ret_frac*1_000_000
    return 100.0*sum(1 for v in _pnls if v <= pnl)/len(_pnls)

def load(sym):
    p = os.path.join(DATA, f"{sym}_1m.csv")
    if not os.path.exists(p): return None
    bars=[]
    with open(p) as f:
        rd=csv.reader(f); next(rd,None)
        for row in rd:
            try: bars.append((float(row[2]),float(row[3]),float(row[4])))  # high,low,close
            except (ValueError,IndexError): pass
    return bars

def simulate(bars, s, length, lev, strat):
    r_stop = 0.01 - 1.0/lev
    cost = COST_BPS/10000.0
    e = 1.0
    pos = 0; entry=None; e_entry=e
    eq=[e]; peak=e; maxdd=0.0; stopped=False
    end=min(s+length, len(bars))
    for i in range(s+1, end):
        h,l,c = bars[i]; pc = bars[i-1][2]
        # desired signal
        if strat=="static":
            sig=1
        else:
            j=i-MOM_LOOKBACK
            sig = (1 if c>bars[j][2] else -1) if j>=s else (pos if pos else 1)
        # open if flat
        if pos==0:
            pos=sig; entry=c; e_entry=e
        # stop-out check on open position (intrabar worst case)
        if pos!=0:
            worst = (l/entry-1) if pos>0 else (1-h/entry)
            if worst <= r_stop:
                e = e_entry*(1+lev*r_stop); stopped=True
                eq.append(e); break
        # mark-to-market at close
        p_ret = (c/entry-1) if pos>0 else (1-c/entry)
        e = e_entry*(1+lev*p_ret)
        eq.append(e)
        peak=max(peak,e); maxdd=max(maxdd,(peak-e)/peak)
        # flip on signal change
        if sig!=pos:
            e *= (1-cost)              # pay spread on the flip
            pos=sig; entry=c; e_entry=e
    final_ret = e-1.0
    # Sharpe of 15-min equity returns
    samp = eq[::15]
    sh=0.0
    if len(samp)>=9:
        rets=[(samp[k]/samp[k-1]-1) for k in range(1,len(samp)) if samp[k-1]>0]
        if len(rets)>=8 and statistics.pstdev(rets)>0:
            sh = statistics.mean(rets)/statistics.pstdev(rets)
    return final_ret, stopped, maxdd, sh

def pctile(xs,q):
    if not xs: return float('nan')
    xs=sorted(xs); i=q/100*(len(xs)-1); lo=int(i); f=i-lo
    return xs[lo]+f*(xs[min(lo+1,len(xs)-1)]-xs[lo])

def run():
    print(f"COST_BPS={COST_BPS} per flip | LEVS={LEVS} | step={STEP}bars | mom_lookback={MOM_LOOKBACK}\n")
    for sym in SYMS:
        bars=load(sym)
        if not bars or len(bars)<3000:
            print(f"=== {sym}: NO/insufficient data ({0 if not bars else len(bars)} bars) ===\n"); continue
        # realised vol context
        rets=[bars[i][2]/bars[i-1][2]-1 for i in range(1,len(bars)) if bars[i-1][2]>0]
        dvol=statistics.pstdev(rets)*math.sqrt(1440)*100
        print(f"=== {sym} | {len(bars):,} bars (~{len(bars)//1440}d) | ~{dvol:.1f}% daily vol ===")
        for wlabel,wlen in WINDOWS.items():
            starts=list(range(0, len(bars)-wlen, STEP))
            print(f"  [{wlabel} rounds, {len(starts)} windows]")
            print(f"  {'strat':>6} {'lev':>4} | {'P_elim':>7} | {'ret p10':>8} {'ret p50':>8} {'ret p90':>8} | {'Shp p50':>7} | {'RetPct@p50':>10} {'RetPct@p90':>10}")
            for strat in ("static","mom"):
                for lev in LEVS:
                    fr=[]; st=0; shs=[]
                    for s in starts:
                        r,stopped,mdd,sh = simulate(bars,s,wlen,lev,strat)
                        if stopped: st+=1
                        else: fr.append(r); shs.append(sh)
                    n=len(starts); pe=st/n
                    p10,p50,p90 = (pctile(fr,10),pctile(fr,50),pctile(fr,90)) if fr else (float('nan'),)*3
                    shp = pctile(shs,50) if shs else float('nan')
                    rp50 = ret_to_pct(p50) if fr else float('nan')
                    rp90 = ret_to_pct(p90) if fr else float('nan')
                    print(f"  {strat:>6} {lev:>4} | {pe*100:6.1f}% | {p10*100:7.1f}% {p50*100:7.1f}% {p90*100:7.1f}% | {shp:7.3f} | {rp50:10.0f} {rp90:10.0f}")
            print()

if __name__=="__main__":
    run()
