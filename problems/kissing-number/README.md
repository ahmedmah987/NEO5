# Kissing numbers

How many unit spheres can touch a central unit sphere without overlapping each other?

In 1694 Newton and David Gregory argued about three dimensions — Newton said 12, Gregory 13. Newton
was right, but it took until 1953 to prove it. In 8 and 24 dimensions the answer is known
exactly, thanks to two extraordinary structures: the **E8 lattice (240)** and the **Leech lattice
(196,560)** — the same lattices behind Maryna Viazovska's Fields-Medal-winning solution of sphere
packing in those dimensions, whose proofs were machine-verified in 2026. In most other dimensions
only bounds are known, and the lower bounds still move: AlphaEvolve raised dimension 11 from 592 to
593 in 2025.

## Solution format

```json
"solution": {"vectors": [[0, 2, -2, 0, ...], ...]}
```

* each vector points from the centre of the middle sphere to a touching sphere;
* coordinates must be **integers** (scale a rational configuration by a common denominator);
* all vectors must have the same length, and every pair must be at least 60 degrees apart:
  `2 * <u, v> <= |u|^2` for all `u != v`.

The verifier ([`unsolved/problems/kissing_number.py`](../../unsolved/problems/kissing_number.py))
checks every pair with exact integer arithmetic. The score is the number of vectors.

## Instances

* **d = 8** is solved (240, the roots of E8). It is here as a warm-up: the seed file
  [`e8-roots.json`](../../submissions/kissing-number/d8/e8-roots.json) shows the format.
* **d = 9 … 16** are open. A first verified file that matches the best-known lower bound is
  already a contribution — many record configurations have never been published as plain
  coordinate lists. Beating a bound would be a mathematical result.
