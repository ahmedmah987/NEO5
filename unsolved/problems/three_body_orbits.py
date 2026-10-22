"""Atlas of periodic orbits of the planar three-body problem.

Setup (Suvakov & Dmitrasinovic 2013; Li & Liao 2017), G = 1, zero angular momentum:
    r1 = (-1, 0), r2 = (1, 0), r3 = (0, 0)
    v1 = v2 = (p1, p2), v3 = -(m1 + m2) (p1, p2) / m3

Solution format: {"p1": "...", "p2": "...", "T": "..."} as decimal literals.
The verifier integrates the orbit with SciPy's DOP853 at rtol = atol = 1e-13 and accepts it
when the full state returns to its start within 1e-7 after time T. It then reduces T to the
minimal period, computes the scale-invariant period T* = T |E|^(3/2), and the orbit's
topology: the cyclic sequence of syzygies (which body is in the middle each time the three
bodies line up), canonicalised over relabelling, time reversal and starting point.
"""

import bisect
import json
import math
from itertools import permutations

import numpy as np
from scipy.integrate import solve_ivp

from ..exact import ExactnessError, to_fraction
from ..model import Result

KIND = "atlas"
RTOL = ATOL = 1e-13
CLOSURE_TOL = 1e-7
MAX_PERIOD = 120
MIN_DISTANCE = 1e-3
SAMPLES_PER_TIME = 2000
CATALOGUE_TOL = 1e-6       # relative tolerance on T* when comparing with published orbits


def initial_state(p1, p2, m):
    v3 = -(m[0] + m[1]) / m[2]
    return np.array([-1.0, 0.0, 1.0, 0.0, 0.0, 0.0, p1, p2, p1, p2, v3 * p1, v3 * p2])


def energy(y, m):
    (x1, y1, x2, y2, x3, y3, u1, w1, u2, w2, u3, w3) = y
    ke = 0.5 * (m[0] * (u1 * u1 + w1 * w1) + m[1] * (u2 * u2 + w2 * w2) + m[2] * (u3 * u3 + w3 * w3))
    pe = -(m[0] * m[1] / math.hypot(x2 - x1, y2 - y1) + m[0] * m[2] / math.hypot(x3 - x1, y3 - y1)
           + m[1] * m[2] / math.hypot(x3 - x2, y3 - y2))
    return ke + pe


def _rhs(m):
    m1, m2, m3 = m

    def f(t, y):
        x1, y1, x2, y2, x3, y3 = y[0], y[1], y[2], y[3], y[4], y[5]
        dx12, dy12 = x2 - x1, y2 - y1
        dx13, dy13 = x3 - x1, y3 - y1
        dx23, dy23 = x3 - x2, y3 - y2
        r12 = (dx12 * dx12 + dy12 * dy12) ** 1.5
        r13 = (dx13 * dx13 + dy13 * dy13) ** 1.5
        r23 = (dx23 * dx23 + dy23 * dy23) ** 1.5
        return [y[6], y[7], y[8], y[9], y[10], y[11],
                m2 * dx12 / r12 + m3 * dx13 / r13, m2 * dy12 / r12 + m3 * dy13 / r13,
                -m1 * dx12 / r12 + m3 * dx23 / r23, -m1 * dy12 / r12 + m3 * dy23 / r23,
                -m1 * dx13 / r13 - m2 * dx23 / r23, -m1 * dy13 / r13 - m2 * dy23 / r23]
    return f


def _middle_body(pos):
    """Index (1-3) of the body lying between the other two in a (near-)collinear configuration."""
    best, mid = math.inf, 0
    for k in range(3):
        a, b = pos[(k + 1) % 3], pos[(k + 2) % 3]
        slack = np.linalg.norm(pos[k] - a) + np.linalg.norm(pos[k] - b) - np.linalg.norm(a - b)
        if slack < best:
            best, mid = slack, k
    return str(mid + 1)


def syzygy_sequence(sol, T):
    """Middle-body labels of the collinear instants in [0, T); the start itself is a syzygy with body 3 in the middle."""
    n = max(20_000, int(SAMPLES_PER_TIME * T))
    ts = np.linspace(0.0, T, n)
    Y = sol.sol(ts)
    area = (Y[2] - Y[0]) * (Y[5] - Y[1]) - (Y[3] - Y[1]) * (Y[4] - Y[0])
    seq = ["3"]
    inner = area[1:-1]
    for k in np.where(np.sign(inner[:-1]) * np.sign(inner[1:]) < 0)[0]:
        i = k + 1
        a0, a1 = area[i], area[i + 1]
        t = ts[i] + (ts[i + 1] - ts[i]) * a0 / (a0 - a1)          # linear interpolation of the crossing
        y = sol.sol(t)
        seq.append(_middle_body(np.array([[y[0], y[1]], [y[2], y[3]], [y[4], y[5]]])))
    return "".join(seq), float(np.min([np.hypot(Y[2] - Y[0], Y[3] - Y[1]).min(),
                                        np.hypot(Y[4] - Y[0], Y[5] - Y[1]).min(),
                                        np.hypot(Y[4] - Y[2], Y[5] - Y[3]).min()]))


def canonical_word(seq):
    """Canonical form over body relabelling, time reversal and rotation; returns (primitive root, power)."""
    best = None
    for perm in permutations("123"):
        table = str.maketrans("123", "".join(perm))
        s = seq.translate(table)
        for t in (s, s[::-1]):
            r = min(t[i:] + t[:i] for i in range(len(t)))
            if best is None or r < best:
                best = r
    L = len(best)
    for p in range(1, L + 1):
        if L % p == 0 and best[:p] * (L // p) == best:
            return best[:p], L // p
    return best, 1


def verify(sub, spec):
    m = [float(x) for x in spec["masses"]]
    try:
        p1 = to_fraction(sub.solution["p1"])
        p2 = to_fraction(sub.solution["p2"])
        T = to_fraction(sub.solution["T"])
    except KeyError as exc:
        return Result(False, error=f"solution is missing {exc}")
    except ExactnessError as exc:
        return Result(False, error=str(exc))
    if not (0 < T <= MAX_PERIOD):
        return Result(False, error=f"period T must be in (0, {MAX_PERIOD}]")
    p1, p2, T = float(p1), float(p2), float(T)
    y0 = initial_state(p1, p2, m)
    E = energy(y0, m)
    if E >= 0:
        return Result(False, error="the system is not bound (energy >= 0)")
    sol = solve_ivp(_rhs(m), (0.0, T), y0, method="DOP853", rtol=RTOL, atol=ATOL, dense_output=True)
    if not sol.success:
        return Result(False, error=f"integration failed: {sol.message}")
    closure = float(np.linalg.norm(sol.y[:, -1] - y0))
    if closure > CLOSURE_TOL:
        return Result(False, error=f"orbit does not close: |X(T) - X(0)| = {closure:.2e} > {CLOSURE_TOL:.0e}")
    seq, dmin = syzygy_sequence(sol, T)
    if dmin < MIN_DISTANCE:
        return Result(False, error=f"near-collision (minimum distance {dmin:.1e}); collisionless orbits only")
    # reduce to the minimal period: the orbit may have been traversed k times
    T_min, seq_min = T, seq
    for k in range(12, 1, -1):
        if len(seq) % k == 0 and seq == seq[: len(seq) // k] * k:
            if np.linalg.norm(sol.sol(T / k) - y0) <= CLOSURE_TOL * 10:
                T_min, seq_min = T / k, seq[: len(seq) // k]
                break
    root, power = canonical_word(seq_min)
    tstar = T_min * abs(E) ** 1.5
    known, kin = match_known(tstar, root, power, spec)
    details = [f"closes to {closure:.1e} after T = {T:.10g} (DOP853, rtol=atol=1e-13)",
               f"minimal period {T_min:.10g}, scale-invariant period T* = {tstar:.6f}",
               f"{len(seq_min)} syzygies per period; topology {root}" + (f"^{power}" if power > 1 else ""),
               f"closest approach {dmin:.3f}"]
    if known:
        details.append(f"published orbit: same T* as {known}")
    else:
        details.append("not found in the bundled catalogues"
                       + (f"; same topology as {', '.join(kin[:2])}" if kin else ""))
    return Result(True, score=None, score_text=f"T* = {tstar:.6f}", details=details,
                  extra=dict(tstar=tstar, T_min=T_min, word=root, power=power, closure=closure,
                             min_distance=dmin, catalogued=known, catalogue_topology=kin, syzygies=len(seq_min)))


_CATALOGUES = {}


def _load_catalogue(cat):
    """Load a catalogue once: ("json", list of entries) or ("tsv", sorted T* list, refs)."""
    key = cat["path"]
    if key not in _CATALOGUES:
        from . import repo_root
        path = repo_root() / cat["path"]
        if cat["format"] == "json":
            with open(path, encoding="utf-8") as f:
                _CATALOGUES[key] = ("json", json.load(f)["orbits"])
        else:
            import gzip
            ts, refs = [], []
            with gzip.open(path, "rt", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#") or not line.strip():
                        continue
                    t, src, i = line.split("\t")
                    ts.append(float(t))
                    refs.append(f"{src} line {int(i)}")
            _CATALOGUES[key] = ("tsv", ts, refs)
    return _CATALOGUES[key]


def match_known(tstar, word, power, spec):
    """(published orbit with the same T*, published orbits with the same topology), across the bundled catalogues."""
    same, kin = None, []
    tol = CATALOGUE_TOL * max(1.0, tstar)
    for cat in spec.get("catalogues", []):
        data = _load_catalogue(cat)
        if data[0] == "json":
            for o in data[1]:
                if same is None and abs(o["tstar"] - tstar) <= tol:
                    same = f"{o['name']} ({cat['name']})"
                if o.get("word") == word and o.get("power") == power:
                    kin.append(f"{o['name']} ({cat['name']})")
        elif same is None:
            ts, refs = data[1], data[2]
            i = bisect.bisect_left(ts, tstar - tol)
            if i < len(ts) and ts[i] <= tstar + tol:
                same = f"{refs[i]} ({cat['name']})"
    return same, kin
