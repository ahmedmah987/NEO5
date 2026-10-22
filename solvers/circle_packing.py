"""Starter solver for circle-packing: maximise the sum of radii of n circles in the unit square.

Multi-start SLSQP followed by basin hopping around the best packing found. It writes a
submission file that the referee can verify exactly (coordinates are rounded and radii
trimmed until the exact rational check passes).

Usage:
  python solvers/circle_packing.py --n 26 --minutes 10 --github YOUR_HANDLE [--seed 1]
"""

import argparse
import json
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


def unpack(z, n):
    return z[:n], z[n:2 * n], z[2 * n:]


def solve_slsqp(z0, n, iters=600):
    iu, ju = np.triu_indices(n, 1)

    def obj(z):
        return -z[2 * n:].sum()

    def obj_grad(z):
        g = np.zeros_like(z)
        g[2 * n:] = -1.0
        return g

    def cons(z):
        x, y, r = unpack(z, n)
        dx, dy, s = x[iu] - x[ju], y[iu] - y[ju], r[iu] + r[ju]
        return np.concatenate([x - r, 1 - x - r, y - r, 1 - y - r, dx * dx + dy * dy - s * s])

    def cons_jac(z):
        x, y, r = unpack(z, n)
        m = len(iu)
        J = np.zeros((4 * n + m, 3 * n))
        I = np.arange(n)
        J[I, I], J[I, 2 * n + I] = 1, -1
        J[n + I, I], J[n + I, 2 * n + I] = -1, -1
        J[2 * n + I, n + I], J[2 * n + I, 2 * n + I] = 1, -1
        J[3 * n + I, n + I], J[3 * n + I, 2 * n + I] = -1, -1
        k = 4 * n + np.arange(m)
        dx, dy, s = x[iu] - x[ju], y[iu] - y[ju], r[iu] + r[ju]
        J[k, iu], J[k, ju] = 2 * dx, -2 * dx
        J[k, n + iu], J[k, n + ju] = 2 * dy, -2 * dy
        J[k, 2 * n + iu], J[k, 2 * n + ju] = -2 * s, -2 * s
        return J

    bounds = [(0, 1)] * (2 * n) + [(0, 0.5)] * n
    res = minimize(obj, z0, jac=obj_grad, method="SLSQP", bounds=bounds,
                   constraints=[{"type": "ineq", "fun": cons, "jac": cons_jac}],
                   options={"maxiter": iters, "ftol": 1e-15})
    ok = np.isfinite(res.fun) and cons(res.x).min() > -1e-9   # SLSQP often stops "unsuccessfully" at a fine optimum
    return res.x, (-res.fun if ok else -np.inf)


def random_start(n, rng):
    x, y = rng.uniform(0.05, 0.95, n), rng.uniform(0.05, 0.95, n)
    r = rng.uniform(0.01, 0.06, n)
    return np.concatenate([x, y, r])


def exact_round(z, n, digits=15):
    """Round to decimal strings and trim radii until the exact rational check passes."""
    x, y, r = unpack(z, n)
    q = Fraction(1, 10 ** digits)
    X = [Fraction(round(v * 10 ** digits), 10 ** digits) for v in x]
    Y = [Fraction(round(v * 10 ** digits), 10 ** digits) for v in y]
    R = [Fraction(int(v * 10 ** digits), 10 ** digits) - 3 * q for v in r]
    for _ in range(50):
        bad = False
        for i in range(n):
            lim = min(X[i], 1 - X[i], Y[i], 1 - Y[i])
            if R[i] > lim:
                R[i], bad = lim - q, True
        for i in range(n):
            for j in range(i + 1, n):
                dx, dy, s = X[i] - X[j], Y[i] - Y[j], R[i] + R[j]
                if dx * dx + dy * dy < s * s:
                    R[i] -= q
                    R[j] -= q
                    bad = True
        if not bad:
            return X, Y, R
    raise RuntimeError("could not make the packing exactly valid")


def to_decimal(f, digits=15):
    s = f"{f.numerator * 10 ** digits // f.denominator:0{digits + 1}d}"
    return f"{s[:-digits]}.{s[-digits:]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--minutes", type=float, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--github", default="your-handle")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    n, rng = args.n, np.random.default_rng(args.seed)
    deadline = time.time() + 60 * args.minutes
    best_z, best = None, -np.inf
    starts = 0
    while time.time() < deadline:
        if best_z is None or rng.random() < 0.3:
            z0 = random_start(n, rng)                     # explore
        else:
            z0 = best_z.copy()                           # basin hopping: perturb the best packing
            k = rng.integers(1, 4)
            idx = rng.choice(n, k, replace=False)
            z0[idx] = rng.uniform(0.05, 0.95, k)
            z0[n + idx] = rng.uniform(0.05, 0.95, k)
            z0[2 * n + idx] = 0.01
            z0[:2 * n] += rng.normal(0, 0.01, 2 * n)
            z0 = np.clip(z0, 0, 1)
        z, val = solve_slsqp(z0, n)
        starts += 1
        if val > best + 1e-12:
            best_z, best = z, val
            print(f"[{starts:5d}] sum of radii = {best:.12f}", flush=True)
    X, Y, R = exact_round(best_z, n)
    total = sum(R)
    print(f"exact sum after rounding: {float(total):.12f}  ({starts} local solves)")
    sub = {"problem": "circle-packing", "instance": f"n{n}", "author": {"github": args.github},
           "method": {"ai": False, "tools": ["solvers/circle_packing.py"],
                      "description": f"multi-start SLSQP + basin hopping, seed {args.seed}, {args.minutes} min"},
           "solution": {"circles": [[to_decimal(a), to_decimal(b), to_decimal(c)] for a, b, c in zip(X, Y, R)]}}
    out = Path(args.out or f"submissions/circle-packing/n{n}/{args.github}-{int(time.time())}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sub, indent=1) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
