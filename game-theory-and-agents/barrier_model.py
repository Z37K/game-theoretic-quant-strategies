"""
The stopping-time model at the centre of the strategy.

Premise: a directional position with no expected edge, so drift is zero while
the variance over the window is real. Under that assumption a leveraged position
with two equity barriers, lock at +T and self-stop at -S, has two closed-form
properties, and they say very different things.

    P(lock before stop) = S / (T + S)          leverage CANCELS
    E[time to resolve]  = T*S / (L^2 * sigma^2)  leverage enters as 1/L^2

So the barrier RATIO sets your probability, and LEVERAGE sets your speed. That
separation is the whole strategy: choose the ratio for the probability you
want, then choose leverage to fit the time you actually have left.

Both results are verified below against a symmetric random walk, which is the
discrete case where the answers are known exactly (gambler's ruin).

    python barrier.py
"""
import math
import random

# BTC has run near 55% annualised. Expressed per minute for the time model.
BTC_ANNUAL_VOL = 0.55
MINUTES_PER_YEAR = 525_600


def p_lock_first(target, stop):
    """P(equity reaches +target before -stop) under zero drift.

    Note what is absent: leverage. It scales both barriers identically in
    price terms, so it divides out entirely.
    """
    return stop / (target + stop)


def expected_minutes(target, stop, leverage, sigma_per_min):
    """Expected time until one barrier is touched.

    Here leverage matters, and quadratically - it is the only lever on speed.
    """
    up = target / leverage
    down = stop / leverage
    return up * down / sigma_per_min ** 2


def sigma_per_minute(annual_vol=BTC_ANNUAL_VOL):
    return annual_vol / math.sqrt(MINUTES_PER_YEAR)


def simulate_window(target, stop, leverage, sigma_per_min, minutes,
                    n=4000, step_min=5, seed=1):
    """Finite-horizon version: lock, stop, or run out of clock.

    The closed form has only two outcomes because it waits forever. A round
    does not wait, so this returns the third one too - the share of windows
    that touch neither barrier and are scored wherever they happen to sit.
    """
    rng = random.Random(seed)
    up = target / leverage
    down = -stop / leverage
    sigma_step = sigma_per_min * math.sqrt(step_min)
    steps = int(minutes / step_min)

    locked = stopped = 0
    for _ in range(n):
        r = 0.0
        for _ in range(steps):
            r += rng.gauss(0.0, sigma_step)
            if r >= up:
                locked += 1
                break
            if r <= down:
                stopped += 1
                break
    unresolved = n - locked - stopped
    return locked / n, stopped / n, unresolved / n


def _walk(a, b, n=20000, seed=1):
    """Symmetric +/-1 walk between +a and -b.

    Exact results: P(hit +a first) = b/(a+b), E[steps] = a*b. Used to confirm
    the continuous formulas rather than to compute anything.
    """
    rng = random.Random(seed)
    wins = 0
    total_steps = 0
    for _ in range(n):
        x = 0
        steps = 0
        while -b < x < a:
            x += 1 if rng.random() < 0.5 else -1
            steps += 1
        if x >= a:
            wins += 1
        total_steps += steps
    return wins / n, total_steps / n


def main():
    sigma = sigma_per_minute()
    target, stop = 0.04, 0.40

    print("=" * 66)
    print("BARRIER RATIO SETS THE PROBABILITY - LEVERAGE DOES NOT")
    print("=" * 66)
    print(f"  target +{target:.0%} equity, self-stop -{stop:.0%} equity")
    print(f"  BTC {BTC_ANNUAL_VOL:.0%} annualised -> sigma = {sigma:.3e} per minute\n")
    print(f"  {'lev':>5} | {'price move to lock':>18} | {'P(lock)':>8} | {'E[resolve]':>12}")
    print("  " + "-" * 56)
    for lev in (2, 4, 8, 16):
        mins = expected_minutes(target, stop, lev, sigma)
        print(f"  {str(lev) + 'x':>5} | {target / lev:>17.2%} | "
              f"{p_lock_first(target, stop):>8.1%} | {mins / 60:>9.1f} hrs")

    print("\n  Identical probability in every row. Only the clock moves.")
    print("  Leverage is chosen to fit the time remaining, nothing else.")

    print("\n" + "=" * 66)
    print("THE RATIO IS THE ONLY THING THAT CHANGES P(LOCK)")
    print("=" * 66)
    print(f"  {'target':>7} {'stop':>7} | {'ratio S/(T+S)':>14} | {'P(lock)':>8}")
    print("  " + "-" * 44)
    for t, s in ((0.04, 0.40), (0.04, 0.20), (0.10, 0.40), (0.02, 0.40)):
        print(f"  {t:>7.0%} {s:>7.0%} | {s / (t + s):>14.4f} | {p_lock_first(t, s):>8.1%}")

    print("\n" + "=" * 66)
    print("VERIFICATION AGAINST THE EXACT DISCRETE CASE")
    print("=" * 66)
    print("  Symmetric walk between +a and -b. Closed form: P = b/(a+b), E[steps] = a*b.")
    print(f"\n  {'a':>4} {'b':>4} | {'sim P':>7} {'exact':>7} | {'sim E[n]':>9} {'exact':>7}")
    print("  " + "-" * 48)
    for a, b in ((4, 40), (8, 40), (4, 20), (10, 10)):
        sim_p, sim_t = _walk(a, b)
        print(f"  {a:>4} {b:>4} | {sim_p:>7.4f} {b / (a + b):>7.4f} | "
              f"{sim_t:>9.1f} {a * b:>7}")

    print("\n" + "=" * 66)
    print("THE FINITE WINDOW - WHERE LEVERAGE ACTUALLY EARNS ITS KEEP")
    print("=" * 66)
    print("  The closed form assumes you wait indefinitely. A round ends on a")
    print("  clock, so a third outcome exists: neither barrier touched. Those")
    print("  windows land on a coin-flip terminal return - the mediocre result")
    print("  the strategy exists to avoid.\n")
    window_h = 48
    print(f"  {window_h}h window, target +{target:.0%}, stop -{stop:.0%}\n")
    print(f"  {'lev':>5} | {'P(lock)':>8} {'P(stop)':>8} {'P(unresolved)':>14}")
    print("  " + "-" * 42)
    for lev in (2, 4, 8, 16):
        lock, stopped, unresolved = simulate_window(
            target, stop, lev, sigma, window_h * 60)
        print(f"  {str(lev) + 'x':>5} | {lock:>7.1%} {stopped:>8.1%} {unresolved:>14.1%}")

    print("\n  Leverage does not improve the odds GIVEN resolution. It raises")
    print("  the chance of resolving at all, converting the unresolved bucket")
    print("  into locked wins.")

    print("\n" + "=" * 66)
    print("WHY NOT JUST HOLD A DIRECTIONAL POSITION?")
    print("=" * 66)
    print("  Same zero-drift market. The only difference is the exit rule.\n")
    print(f"  hold to the cutoff, no edge   -> P(top quartile) ~ {0.25:.0%}  (symmetric outcome)")
    print(f"  leveraged position + barriers -> P(lock target)  ~ {p_lock_first(target, stop):.0%}")
    print("\n  The stopping rule surrenders unbounded upside, which rank")
    print("  saturation had already made worthless, and buys a high")
    print("  probability of the finite target that actually reaches the rank.")


if __name__ == "__main__":
    main()
