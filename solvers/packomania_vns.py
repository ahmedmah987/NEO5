"""Variable-neighbourhood search around a published 'max sum of radii' packing (square [-1/2, 1/2]^2).

Move: pick a random spot, take the k nearest circles, perturb them (jiggle / swap / reinsert the
smallest into the biggest local hole), repair to exact feasibility, then re-optimise everything
with sequential LPs (convex-underestimating linearisation, so steps stay feasible). Keep the
result if the sum of radii improves.

Input is a Packomania csqv coordinate file (square [-1/2, 1/2]^2, lines "i x y r").
This is the search that improved the N = 450 record on 23 Oct 2026.

Usage: python solvers/packomania_vns.py <csqvN.txt> <minutes> <seed> <out_prefix>
"""
import sys
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, vstack
from scipy.spatial import cKDTree

LP_OPTS = {"primal_feasibility_tolerance": 1e-10, "dual_feasibility_tolerance": 1e-10}


def load(path):
    rows = [list(map(float, l.split()[-3:])) for l in open(path) if l.strip() and not l.startswith("#")]
    a = np.array(rows)
    return a[:, 0].copy(), a[:, 1].copy(), a[:, 2].copy()


def near_pairs(x, y, r, margin):
    tree = cKDTree(np.c_[x, y])
    cand = tree.query_pairs(2 * r.max() + margin, output_type="ndarray")
    if len(cand) == 0:
        return cand[:, 0], cand[:, 1]
    i, j = cand[:, 0], cand[:, 1]
    keep = np.hypot(x[i] - x[j], y[i] - y[j]) - r[i] - r[j] < margin
    return i[keep], j[keep]


def repair(x, y, r):
    """Shrink radii until the packing is feasible (to 1e-15 slack)."""
    for _ in range(200):
        r[:] = np.minimum(r, np.minimum(0.5 - np.abs(x), 0.5 - np.abs(y)) - 1e-15)
        i, j = near_pairs(x, y, r, 1e-12)
        if len(i) == 0:
            break
        over = r[i] + r[j] - np.hypot(x[i] - x[j], y[i] - y[j])
        bad = over > -1e-15
        if not bad.any():
            break
        cut = np.zeros_like(r)
        np.maximum.at(cut, i[bad], over[bad] / 2 + 1e-15)
        np.maximum.at(cut, j[bad], over[bad] / 2 + 1e-15)
        r -= cut
    np.maximum(r, 1e-6, out=r)
    return x, y, r


def slp(x, y, r, delta=1e-3, min_delta=1e-10, max_iter=200):
    n = len(x)
    I = np.arange(n)
    for _ in range(max_iter):
        i, j = near_pairs(x, y, r, 4 * delta)
        dx, dy = x[i] - x[j], y[i] - y[j]
        d = np.hypot(dx, dy)
        ux, uy = dx / d, dy / d
        m = len(i)
        rows = np.repeat(np.arange(m), 6)
        cols = np.stack([i, j, n + i, n + j, 2 * n + i, 2 * n + j], 1).ravel()
        vals = np.stack([-ux, ux, -uy, uy, np.ones(m), np.ones(m)], 1).ravel()
        A_pair = coo_matrix((vals, (rows, cols)), shape=(m, 3 * n))
        wr, wc, wv, wb = [], [], [], []
        for k, (col, sgn, coord) in enumerate([(0, 1, x), (0, -1, x), (n, 1, y), (n, -1, y)]):
            wr += [k * n + I, k * n + I]
            wc += [col + I, 2 * n + I]
            wv += [np.full(n, float(sgn)), np.ones(n)]
            wb.append(0.5 - sgn * coord - r)
        A_wall = coo_matrix((np.concatenate(wv), (np.concatenate(wr), np.concatenate(wc))), shape=(4 * n, 3 * n))
        A = vstack([A_pair, A_wall]).tocsr()
        b = np.concatenate([d - r[i] - r[j], np.concatenate(wb)])
        c = np.r_[np.zeros(2 * n), -np.ones(n)]
        res = linprog(c, A_ub=A, b_ub=b, bounds=[(-delta, delta)] * (3 * n), method="highs", options=LP_OPTS)
        if res.status != 0:
            delta *= 0.3
            if delta < min_delta:
                break
            continue
        s = res.x
        nx, ny, nr = x + s[:n], y + s[n:2 * n], r + s[2 * n:]
        nx, ny, nr = repair(nx, ny, nr)
        if nr.sum() > r.sum() + 1e-14:
            x, y, r = nx, ny, nr
            if -res.fun < 0.25 * delta * n * 1e-3:
                delta *= 0.5
        else:
            delta *= 0.3
            if delta < min_delta:
                break
    return x, y, r


def perturb(x, y, r, rng):
    n = len(x)
    x, y, r = x.copy(), y.copy(), r.copy()
    k = int(rng.integers(4, 25))
    centre = rng.uniform(-0.5, 0.5, 2)
    idx = np.argsort((x - centre[0]) ** 2 + (y - centre[1]) ** 2)[:k]
    move = rng.integers(3)
    if move == 0:                                   # jiggle a neighbourhood
        s = r[idx].mean()
        x[idx] += rng.normal(0, 0.3 * s, k)
        y[idx] += rng.normal(0, 0.3 * s, k)
        r[idx] *= 0.7
    elif move == 1:                                 # swap two circles of different size
        a, b = rng.choice(idx, 2, replace=False)
        x[a], x[b], y[a], y[b] = x[b], x[a], y[b], y[a]
        r[a] = r[b] = min(r[a], r[b]) * 0.8
    else:                                           # move the smallest circle into a local hole
        s = idx[np.argmin(r[idx])]
        pts = rng.uniform(-0.5, 0.5, (400, 2))
        tree = cKDTree(np.c_[x, y])
        dist, near = tree.query(pts, k=6)
        clearance = (dist - r[near]).min(1)
        p = pts[np.argmax(clearance)]
        x[s], y[s], r[s] = p[0], p[1], max(clearance.max(), 1e-4) * 0.9
    x = np.clip(x, -0.499, 0.499)
    y = np.clip(y, -0.499, 0.499)
    return repair(x, y, r)


def main():
    path, minutes, seed, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    rng = np.random.default_rng(seed)
    x, y, r = repair(*load(path))
    x, y, r = slp(x, y, r, delta=1e-6)
    best = r.sum()
    start = best
    print(f"{path}: N={len(x)} start {best:.13f}", flush=True)
    t_end = time.time() + 60 * minutes
    moves = 0
    while time.time() < t_end:
        px, py, pr = perturb(x, y, r, rng)
        px, py, pr = slp(px, py, pr, delta=3e-3)
        moves += 1
        if pr.sum() > best + 1e-12:
            x, y, r, best = px, py, pr, pr.sum()
            print(f"  move {moves}: NEW BEST {best:.13f}  (+{best - start:.3e})", flush=True)
            np.savetxt(out + ".best.txt", np.c_[x, y, r], fmt="%.17f")
    print(f"done: {moves} moves, best {best:.13f}, improvement {best - start:.3e}", flush=True)


if __name__ == "__main__":
    main()
