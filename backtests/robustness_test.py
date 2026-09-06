"""
robustness_test.py - harden the flatten-at-target plan before it becomes a live spec.
Research only (cached crypto-data). Three checks:

(1) ADAPTIVE LADDER (the real rule): hold for T_hi (Top-10); in the last LATE_H hours
    ratchet the target down to T_lo (Top-25 floor). Flatten at whichever target the
    time-varying threshold is currently set to. Measures P(Top-10), P(Top-25 floor),
    P(hard-DQ), P(hold) and E[RetPct] vs the fixed-target numbers.

(2) SELF-IMPOSED STOP: voluntarily flatten at a survivable loss (e.g. -20% equity)
    instead of riding to the hard 30%-margin DQ (which at 8x = ~-92% equity / -11.5%
    price). Shows the trade: a self-stop converts catastrophic DQ into a survivable
    loss, at some cost to win-rate.

(3) COIN COMPARISON at the chosen config (low-vol BTC vs higher-vol ETH/SOL).

Direction = BTC trailing-12h sign (the validated edge). 48h windows, rolled 6h.
Pure stdlib.
"""
import os, csv, statistics

HERE=os.path.dirname(os.path.abspath(__file__)); DATA=os.path.join(HERE,"crypto-data")
SYMS=["BTCUSD","ETHUSD","SOLUSD","XRPUSD"]
WLEN=2880; STEP=360; BTC_TREND=720
T_HI=0.12; T_LO=0.04; LATE_H=8           # ratchet to T_LO in the last 8h
LATE_BARS=LATE_H*60

_pnls=sorted(float(r["pnl"]) for r in csv.DictReader(open(os.path.join(HERE,"..","scoreboard-analysis","leaderboard_1830.csv"),encoding="utf-8")))
def ret_to_pct(r):
    pnl=r*1_000_000; return 100.0*sum(1 for v in _pnls if v<=pnl)/len(_pnls)

def load(sym):
    p=os.path.join(DATA,f"{sym}_1m.csv"); H=[];L=[];C=[]
    with open(p) as f:
        rd=csv.reader(f); next(rd,None)
        for row in rd:
            try: H.append(float(row[2]));L.append(float(row[3]));C.append(float(row[4]))
            except (ValueError,IndexError): pass
    return H,L,C

def sim_ladder(H,L,C,s,lev,direction,self_stop_eq=None):
    """Returns outcome string + locked return. Time-varying target: T_HI until the
    last LATE_BARS, then T_LO. self_stop_eq: voluntary exit equity (e.g. 0.80)."""
    entry=C[s]; r_hardstop=0.01-1.0/lev
    end=min(s+WLEN,len(C)); switch=end-LATE_BARS
    for i in range(s+1,end):
        if direction>0: worst_pr=L[i]/entry-1; best_pr=H[i]/entry-1
        else:           worst_pr=1-H[i]/entry; best_pr=1-L[i]/entry
        eq_worst=1+lev*worst_pr; eq_best=1+lev*best_pr
        # hard DQ first (conservative intrabar ordering)
        if worst_pr<=r_hardstop: return "DQ", -1.0
        # voluntary self-stop (survivable loss)
        if self_stop_eq is not None and eq_worst<=self_stop_eq:
            return "self_stop", self_stop_eq-1
        tgt = T_HI if i<switch else T_LO
        if eq_best>=1+tgt:
            return ("win_hi" if i<switch else "win_lo"), tgt
    pr=(C[end-1]/entry-1) if direction>0 else (1-C[end-1]/entry)
    return "hold", 1+lev*pr-1

def evaluate(sym,lev,self_stop_eq,btcC):
    H,L,C=load(sym); n=min(len(C),len(btcC))
    starts=list(range(BTC_TREND,n-WLEN,STEP))
    cnt={"win_hi":0,"win_lo":0,"self_stop":0,"DQ":0,"hold":0}; rps=[]
    for s in starts:
        d=1 if btcC[s]>btcC[s-BTC_TREND] else -1
        o,r=sim_ladder(H,L,C,s,lev,d,self_stop_eq)
        cnt[o]+=1
        rps.append(0.0 if o=="DQ" else ret_to_pct(r))
    tot=len(starts)
    return tot,{k:v/tot*100 for k,v in cnt.items()},statistics.mean(rps)

def main():
    btcC=load("BTCUSD")[2]
    print("(1)+(3) ADAPTIVE LADDER (T_hi=12%->T_lo=4% last 8h), NO self-stop, by coin & lev")
    print(f"  {'coin':>6} {'lev':>3} | {'Top10':>6} {'Top25':>6} {'hold':>6} {'DQ':>5} | {'E[RetPct]':>9}")
    for sym in SYMS:
        for lev in (5,8):
            tot,p,erp=evaluate(sym,lev,None,btcC)
            print(f"  {sym:>6} {lev:>3} | {p['win_hi']:5.1f}% {p['win_lo']:5.1f}% {p['hold']:5.1f}% {p['DQ']:4.1f}% | {erp:9.1f}")
    print()
    print("(2) SELF-IMPOSED STOP at 8x (ETH): convert DQ -> survivable loss")
    print(f"  {'self_stop':>10} | {'Top10':>6} {'Top25':>6} {'hold':>6} {'selfstop':>8} {'DQ':>5} | {'E[RetPct]':>9}")
    for ss in (None,0.80,0.70,0.60):
        tot,p,erp=evaluate("ETHUSD",8,ss,btcC)
        lab="none" if ss is None else f"{int((1-ss)*100)}% loss"
        print(f"  {lab:>10} | {p['win_hi']:5.1f}% {p['win_lo']:5.1f}% {p['hold']:5.1f}% {p['self_stop']:7.1f}% {p['DQ']:4.1f}% | {erp:9.1f}")

if __name__=="__main__":
    main()
