"""Starter solver for the three-body orbit atlas.

Random starting velocities are integrated; every time the state comes back close to where it
started, a Levenberg-Marquardt shooting step tries to close the orbit exactly. Closed orbits are
checked with the repository's own verifier, and those not yet in the atlas are written as
ready-to-submit files.

Usage:
  python solvers/three_body.py --seeds 400 --github YOUR_HANDLE [--tmax 40] [--seed 1]
"""

import argparse
import json
import math
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unsolved.model import Submission                      # noqa: E402
from unsolved.problems import load_meta, three_body_orbits as tb   # noqa: E402
from unsolved.records import compute, same_orbit           # noqa: E402

M = (1.0, 1.0, 1.0)
RHS = tb._rhs(M)


def flow(p1, p2, T, rtol):
    y0 = tb.initial_state(p1, p2, M)
    return y0, solve_ivp(RHS, (0, T), y0, method="DOP853", rtol=rtol, atol=rtol, dense_output=True)


def near_returns(p1, p2, tmax, thresh=1.0):
    y0, sol = flow(p1, p2, tmax, 1e-9)
    if not sol.success:
        return []
    ts = np.linspace(1.0, sol.t[-1], int(200 * tmax))
    d = np.linalg.norm(sol.sol(ts) - y0[:, None], axis=0)
    idx = np.where((d[1:-1] < thresh) & (d[1:-1] <= d[:-2]) & (d[1:-1] <= d[2:]))[0] + 1
    return sorted(((ts[i], d[i]) for i in idx), key=lambda x: x[1])[:3]


def shoot(p1, p2, T):
    def resid(z):
        y0, sol = flow(z[0], z[1], z[2], 1e-12)
        return sol.y[:, -1] - y0
    r = least_squares(resid, [p1, p2, T], method="lm", xtol=1e-14, ftol=1e-14, max_nfev=200)
    return r.x, float(np.linalg.norm(r.fun))


def work(seed_and_tmax):
    seed, tmax = seed_and_tmax
    rng = np.random.default_rng(seed)
    while True:                                   # bound initial conditions only
        p1, p2 = rng.uniform(0.05, 0.65), rng.uniform(0.0, 0.65)
        if 3 * (p1 * p1 + p2 * p2) < 2.4:
            break
    found = []
    for t, _ in near_returns(p1, p2, tmax):
        try:
            z, err = shoot(p1, p2, t)
        except Exception:
            continue
        if err < 1e-9 and 0.5 < z[2] < 1.5 * tmax:
            found.append(tuple(float(v) for v in z))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--tmax", type=float, default=40.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--github", default="your-handle")
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count()))
    args = ap.parse_args()

    with mp.Pool(args.workers) as pool:
        candidates = [c for r in pool.imap_unordered(work, [(args.seed * 1_000_003 + i, args.tmax)
                                                           for i in range(args.seeds)]) for c in r]
    print(f"{len(candidates)} closed orbits from {args.seeds} seeds; checking them with the verifier...")

    spec = load_meta("three-body-orbits")["instances"]["equal-mass"]
    _, standings, _ = compute()
    atlas = list(standings["three-body-orbits"]["equal-mass"]["atlas"])
    out_dir = ROOT / "submissions" / "three-body-orbits" / "equal-mass"
    new = 0
    for p1, p2, T in candidates:
        sub = Submission(path=Path("candidate.json"), problem="three-body-orbits", instance="equal-mass",
                         author={"github": args.github}, method={}, solution={"p1": repr(p1), "p2": repr(p2), "T": repr(T)})
        res = tb.verify(sub, spec)
        if not res.valid or any(same_orbit(o, res.extra) for o in atlas):
            continue
        atlas.append(res.extra)
        new += 1
        x = res.extra
        doc = {"problem": "three-body-orbits", "instance": "equal-mass", "author": {"github": args.github},
               "method": {"ai": False, "tools": ["solvers/three_body.py"],
                          "description": f"random seeds + shooting, seed {args.seed}"},
               "solution": {"p1": repr(p1), "p2": repr(p2), "T": repr(x["T_min"])}}
        path = out_dir / f"{args.github}-tstar-{x['tstar']:.4f}.json"
        path.write_text(json.dumps(doc, indent=2) + "\n")
        label = f"published: {x['catalogued']}" if x["catalogued"] else "NOT in the bundled catalogues"
        print(f"  new to the atlas: T* = {x['tstar']:.6f}  {label}  -> {path.relative_to(ROOT)}")
    print(f"{new} orbit(s) new to the atlas written. Open a pull request with them!")


if __name__ == "__main__":
    main()
