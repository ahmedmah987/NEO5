# Three-body orbit atlas

Newton posed the three-body problem in 1687; Poincaré showed in 1890 that it has no general
solution. What it does have are **periodic orbits** — special starting conditions after which the
three bodies return exactly to where they began. For three centuries only a handful were known.
Then the figure-eight was found (1993, proved 2000), 13 new families appeared in 2013, Li & Liao
listed 695 in 2017, and in 2025 a single search reported over ten thousand three-dimensional ones.
The map is still being drawn — this atlas is a public, verified version of it.

## Setup

Equal masses, `G = 1`, zero angular momentum, the standard isosceles collinear start:

```
r1 = (-1, 0)   r2 = (1, 0)   r3 = (0, 0)
v1 = v2 = (p1, p2)           v3 = -2 (p1, p2)
```

## Solution format

```json
"solution": {"p1": "0.3471168881", "p2": "0.5327249454", "T": "6.3259139829"}
```

## What the verifier checks

[`unsolved/problems/three_body_orbits.py`](../../unsolved/problems/three_body_orbits.py)
integrates the orbit with SciPy's DOP853 (rtol = atol = 1e-13) and accepts it if

* the system is bound (energy < 0) and `T <= 120`,
* the full state returns to its start within `1e-7` after time `T`,
* the bodies never come closer than `1e-3` (collisionless orbits only).

It then reduces `T` to the minimal period and records two fingerprints:

* the **scale-invariant period** `T* = T |E|^(3/2)`, which identifies the orbit;
* the **topology** — the cyclic sequence of syzygies (which body is in the middle each time the
  three line up), canonicalised over relabelling, time reversal and starting point.

## Credit and honesty

* The first verified file for an orbit puts that orbit in the atlas under its author's name.
  Re-submitting a known orbit is valid but earns nothing new.
* Each orbit is compared with two published catalogues bundled in [`catalogues/`](catalogues/):
  [Li & Liao (2017)](https://arxiv.org/abs/1705.00527), 695 families with their topologies, and
  [Hristov & Hristova (2024)](https://arxiv.org/abs/2404.16526) with its December 2024 supplement,
  about 211,000 distinct solutions with T* up to 211. "Not in the bundled catalogues" still does
  not prove "never published" — other catalogues exist, and adding them is a welcome contribution.
* This setup is already mapped in great detail: all 22 orbits seeded here turned out to be
  published. New ground is more likely at longer periods, with unequal masses, or in 3D — each a
  natural next instance for this atlas.
* Different orbits can share a topology (the same "braid" with a different period); the record
  tables say so explicitly.

## Getting started

```bash
python solvers/three_body.py --seeds 400 --github your-handle   # about 15 s per seed per CPU core
```
