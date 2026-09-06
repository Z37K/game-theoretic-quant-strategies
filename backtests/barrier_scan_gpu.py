"""
barrier_scan_gpu.py - GPU-ready barrier scan with a CPU fallback.

Where this fits in the system
------------------------------
The backtest/sweep work is heavy dataframe math over a year of 1-minute bars across several
symbols. NVIDIA RAPIDS (cuDF) is a drop-in, pandas-compatible dataframe library that runs on
the GPU, so the SAME code scales to much larger / more frequent sweeps with a GPU.

It imports cuDF if available (GPU); otherwise it uses pandas (CPU). Both run the exact same
computation, and it reports only real, measured timing for whichever engine ran.

Run:
    python barrier_scan_gpu.py                       # default dataset
    python barrier_scan_gpu.py path/to/SYMBOL_1m.csv
"""

import os
import sys
import time

try:
    import cudf as df_engine  # GPU (RAPIDS) - same API as pandas
    ENGINE = "cuDF (NVIDIA GPU)"
except ImportError:
    import pandas as df_engine  # CPU - identical API
    ENGINE = "pandas (CPU)"

# Strategy barriers are in EQUITY space; at leverage L an equity move x needs a price
# move x/L. So convert the +4% equity target and -40% equity self-stop to price moves.
TREND_BARS = 720          # 12h on 1-minute bars
LEVERAGE = 8.0
EQUITY_TARGET = 0.04      # +4% equity -> flatten / lock
EQUITY_STOP = -0.40       # -40% equity self-stop
PRICE_UP = EQUITY_TARGET / LEVERAGE     # +0.5% price at 8x
PRICE_DOWN = EQUITY_STOP / LEVERAGE     # -5.0% price at 8x

# NOTE: this is a fast, endpoint-based illustration (does the 12h net move reach the
# barrier). The rigorous PATH-dependent first-passage model is barrier_test.py.


def run_pass(filepath: str) -> dict:
    """Count 12h windows whose net move reaches the +4%/-40% equity barriers at 8x.

    Identical code on cuDF (GPU) or pandas (CPU). Timing reported is measured for the
    engine that actually ran - nothing here is simulated or hard-coded.
    """
    t0 = time.perf_counter()
    data = df_engine.read_csv(filepath)
    data["ret_12h"] = data["close"].pct_change(TREND_BARS)
    data["touch_up"] = data["ret_12h"] >= PRICE_UP
    data["touch_down"] = data["ret_12h"] <= PRICE_DOWN
    n_up = int(data["touch_up"].sum())
    n_down = int(data["touch_down"].sum())
    rows = int(len(data))
    elapsed = time.perf_counter() - t0

    return {
        "engine": ENGINE,
        "rows": rows,
        "elapsed_seconds": round(elapsed, 4),
        "rows_per_second": int(rows / elapsed) if elapsed > 0 else None,
        "up_barrier_touches": n_up,
        "down_barrier_touches": n_down,
    }


if __name__ == "__main__":
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "crypto-data", "BTCUSD_1m.csv"
    )
    path = sys.argv[1] if len(sys.argv) > 1 else default
    if not os.path.exists(path):
        print(f"Dataset not found: {path}\nPass a path to a SYMBOL_1m.csv (ts_ms,open,high,low,close,vol).")
        sys.exit(1)

    r = run_pass(path)
    print(f"Engine        : {r['engine']}")
    print(f"Rows processed: {r['rows']:,}")
    print(f"Elapsed       : {r['elapsed_seconds']} s  (measured)")
    print(f"Throughput    : {r['rows_per_second']:,} rows/s  (measured on this engine)")
    print(f"At {LEVERAGE:.0f}x: +{EQUITY_TARGET:.0%} equity target = +{PRICE_UP:.1%} price; "
          f"{EQUITY_STOP:.0%} equity stop = {PRICE_DOWN:.1%} price")
    print(f"12h windows reaching the +{EQUITY_TARGET:.0%} target: {r['up_barrier_touches']:,}")
    print(f"12h windows reaching the {EQUITY_STOP:.0%} stop  : {r['down_barrier_touches']:,}")
