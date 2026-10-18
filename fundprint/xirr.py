"""Our own XIRR, so the app does not need pyxirr (which has no browser build).

Day count is actual days / 365, the same as Excel and pyxirr.
"""
import numpy as np


def xirr(dates, amounts):
    """Annualised return for dated cash flows, as a fraction (0.12 = 12%).

    Returns NaN when no sensible answer exists (for example, all flows have
    the same sign).
    """
    d = np.array([np.datetime64(x, "D") for x in dates])
    a = np.asarray(amounts, dtype=float)
    order = np.argsort(d, kind="stable")
    d, a = d[order], a[order]
    if len(a) < 2 or not (a < 0).any() or not (a > 0).any():
        return float("nan")

    t = (d - d[0]).astype(float) / 365.0

    # Two flows: the answer has a simple closed form
    if len(a) == 2:
        if a[0] < 0 < a[1] and t[1] > 0:
            return float((a[1] / -a[0]) ** (1.0 / t[1]) - 1.0)
        return float("nan")

    def npv(r):
        return float(np.sum(a / (1.0 + r) ** t))

    def slope(r):
        return float(np.sum(-t * a / (1.0 + r) ** (t + 1.0)))

    # Newton's method, starting from the simple gain clamped to a safe range
    r = min(max(a[a > 0].sum() / -a[a < 0].sum() - 1.0, -0.9), 0.1)
    for _ in range(50):
        f, df = npv(r), slope(r)
        if df == 0 or not np.isfinite(f):
            break
        step = f / df
        r_new = r - step
        if r_new <= -1.0:
            break
        if abs(r_new - r) < 1e-9:
            return float(r_new)
        r = r_new

    # Fallback: find a root by halving the range. Same bounds the old solver used.
    return _bracket(npv, -0.999999, 100.0)


def _bracket(npv, lo, hi):
    """A root of npv between lo and hi, or NaN when the ends do not change sign."""
    try:
        flo, fhi = npv(lo), npv(hi)
    except (ArithmeticError, OverflowError, ValueError):
        return float("nan")
    if not np.isfinite(flo) or not np.isfinite(fhi) or flo * fhi > 0:
        return float("nan")
    if flo == 0.0:
        return float(lo)
    for _ in range(80):
        if hi - lo < 1e-12:
            break
        mid = (lo + hi) / 2.0
        try:
            fm = npv(mid)
        except (ArithmeticError, OverflowError, ValueError):
            return float("nan")
        if not np.isfinite(fm):
            return float("nan")
        if fm == 0.0:
            return float(mid)
        if flo * fm < 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return float((lo + hi) / 2.0)
