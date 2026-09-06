"""
barrier_test.py - model the FLATTEN-AT-TARGET strategy as a double-barrier
first-passage problem over the 48h finals window.

We hold a leveraged directional crypto position and:
  - if equity ever TOUCHES 1+T  -> flatten, lock +T  (WIN)
  - if equity ever hits the 30% stop-out (price moves ~1/L against us) -> ELIM
  - else -> hold to window end, take terminal return  (HOLD)

Key asymmetry: at leverage L, a +T equity target = only +T/L price move, while
stop-out = ~1/L price move against. Optional stopping turns crypto vol into a
high-prob touch of a modest target.

Outcome return per window -> leaderboard ReturnPct -> we report P_win, P_elim,
and E[ReturnPct] (the expected percentile this puts us at). Direction modes:
  'long' : always long
  'edge' : long if BTC trailing-12h return > 0 else short (the validated edge)

Pure stdlib. 48h windows, rolled every 6h across 1yr.
"""
import os, csv, statistics

HERE=os.path.dirname(os.path.abspath(__file__)); DATA=os.path.join(HERE,"crypto-data")
SYMS=["BTCUSD","ETHUSD","SOLUSD","XRPUSD","BARUSD"]
WLEN=2880; STEP=360
LEVS=[3,5,8,12]
TARGETS=[0.02,0.04,0.07,0.12,0.20]   # equity targets to flatten at
BTC_TREND=720                         # 12h trailing for edge direction

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

def window_outcome(H,L,C,s,lev,direction):
    """Returns (max_equity_before_stop, terminal_equity, stopped). Single fixed-
    notional entry at s; direction +1 long / -1 short. equity=1+lev*p_ret."""
    entry=C[s]
    r_stop=0.01-1.0/lev          # p_ret stop level (equity = 1+lev*r_stop ~ 0.01*lev)
    end=min(s+WLEN,len(C))
    max_eq=1.0; stopped=False
    for i in range(s+1,end):
        if direction>0:
            worst_pr=L[i]/entry-1; best_pr=H[i]/entry-1      # long: low worst, high best
        else:
            worst_pr=1-H[i]/entry; best_pr=1-L[i]/entry      # short: high worst, low best
        # conservative intrabar order: check stop FIRST (assume adverse extreme came first)
        if worst_pr<=r_stop:
            stopped=True; break
        eq_best=1+lev*best_pr
        if eq_best>max_eq: max_eq=eq_best
    # terminal
    pr=(C[end-1]/entry-1) if direction>0 else (1-C[end-1]/entry)
    term=1+lev*pr
    return max_eq, term, stopped

def run():
    btcH,btcL,btcC=load("BTCUSD")
    print(f"48h windows, flatten-at-target. LEVS={LEVS} TARGETS={[int(t*100) for t in TARGETS]}%\n")
    for sym in SYMS:
        H,L,C=load(sym); n=min(len(C),len(btcC))
        starts=list(range(BTC_TREND, n-WLEN, STEP))
        print(f"=== {sym} ({len(starts)} windows) ===")
        for mode in ("long","edge"):
            print(f"  mode={mode}")
            print(f"  {'lev':>3} {'T%':>4} | {'P_win':>6} {'P_elim':>6} {'P_hold':>6} | {'E[RetPct]':>9} | {'win RetPct':>10}")
            for lev in LEVS:
                for T in TARGETS:
                    win=elim=hold=0; ret_pcts=[]
                    for s in starts:
                        if mode=="edge":
                            d=1 if btcC[s]>btcC[s-BTC_TREND] else -1
                        else:
                            d=1
                        max_eq,term,stopped=window_outcome(H,L,C,s,lev,d)
                        if max_eq>=1+T:
                            # max_eq only accumulates on pre-stop bars (we break on stop),
                            # so this == target touched BEFORE any stop-out -> a clean win
                            win+=1; ret_pcts.append(ret_to_pct(T))
                        elif stopped:
                            elim+=1; ret_pcts.append(0.0)
                        else:
                            hold+=1; ret_pcts.append(ret_to_pct(term-1))
                    tot=len(starts)
                    e_rp=statistics.mean(ret_pcts)
                    print(f"  {lev:>3} {int(T*100):>4} | {win/tot*100:5.1f}% {elim/tot*100:5.1f}% {hold/tot*100:5.1f}% | {e_rp:9.1f} | {ret_to_pct(T):10.0f}")
            print()

if __name__=="__main__":
    run()
