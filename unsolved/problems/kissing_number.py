"""Kissing configurations: as many unit spheres as possible touching one central unit sphere in d dimensions.

Solution format: {"vectors": [[int, ...], ...]} — integer vectors, all of the same length,
pointing from the centre to each touching sphere (scale any rational configuration to integers).
Valid when every pair is at least 60 degrees apart, i.e. 2 * <u, v> <= |u|^2 for all u != v.
The score is the number of vectors.
"""

import numpy as np

from ..exact import ExactnessError, to_int
from ..model import Result

KIND = "max"
MAX_VECTORS = 250_000
MAX_ABS_COORD = 1 << 20      # keeps every dot product far inside int64


def verify(sub, spec):
    d = spec["d"]
    vectors = sub.solution.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        return Result(False, error="solution.vectors must be a non-empty list")
    if len(vectors) > MAX_VECTORS:
        return Result(False, error=f"at most {MAX_VECTORS} vectors are accepted")
    try:
        for i, v in enumerate(vectors):
            if not isinstance(v, list) or len(v) != d:
                return Result(False, error=f"vector {i}: expected {d} integer coordinates")
            for c in v:
                if abs(to_int(c)) > MAX_ABS_COORD:
                    return Result(False, error=f"vector {i}: coordinates must be at most 2^20 in size")
    except ExactnessError as exc:
        return Result(False, error=str(exc))
    V = np.array(vectors, dtype=np.int64)
    norms = (V * V).sum(axis=1)
    if norms[0] == 0:
        return Result(False, error="the zero vector is not a direction")
    if not np.all(norms == norms[0]):
        return Result(False, error="all vectors must have the same length")
    N = int(norms[0])
    k = len(V)
    chunk = max(1, 4_000_000 // k)
    for start in range(0, k, chunk):
        G = V[start:start + chunk] @ V.T                     # exact int64 dot products
        rows = np.arange(start, min(start + chunk, k))
        G[np.arange(len(rows)), rows] = -N                   # ignore each vector's dot with itself
        worst = int(G.max())
        if 2 * worst > N:
            i, j = np.unravel_index(int(G.argmax()), G.shape)
            i = int(rows[i])
            what = "are identical" if worst == N else "are closer than 60 degrees"
            return Result(False, error=f"vectors {i} and {int(j)} {what}")
    return Result(True, score=k, score_text=str(k),
                  details=[f"{k} touching spheres in dimension {d}; every pair at least 60 degrees apart "
                           f"(exact integer arithmetic, |v|^2 = {N})"])
