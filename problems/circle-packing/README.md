# Circle packing: maximise the sum of radii

Place **n** circles inside the unit square so that no two overlap, and make the **sum of their
radii** as large as possible. The circles may have different sizes.

The cases n = 26 and n = 32 became a public benchmark for AI-driven discovery after Google
DeepMind's AlphaEvolve (May 2025) improved the best known values; open-source evolutionary
frameworks and classical optimisers have competed on them since. They are ideal for this record
book: a solution is 3n numbers, and checking it is exact and instant.

## Solution format

```json
"solution": {"circles": [["x", "y", "r"], ...]}
```

* exactly n rows of centre `x`, `y` and radius `r`, written as decimal literals or `"p/q"` strings;
* every circle must lie inside `[0, 1] x [0, 1]` (touching the boundary is allowed);
* no two circles may overlap (touching is allowed).

The verifier ([`unsolved/problems/circle_packing.py`](../../unsolved/problems/circle_packing.py))
checks all of this in exact rational arithmetic. The score is the exact sum of the radii.

## Getting started

```bash
python solvers/circle_packing.py --n 26 --minutes 10 --github your-handle
```

The starter solver (multi-start SLSQP with basin hopping) writes a ready-to-submit file. On one
CPU core it reaches about **2.6266 for n = 26** and **2.9294 for n = 32** in 20 minutes — short of
the published records. Closing that gap is the challenge.
