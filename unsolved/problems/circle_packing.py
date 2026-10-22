"""Circle packing in the unit square: maximise the sum of radii of n disjoint circles.

Solution format: {"circles": [[x, y, r], ...]}  (exactly n rows; numbers as decimal literals or
"p/q" strings). Every check is done in exact rational arithmetic: a circle must lie inside
[0, 1]^2 and no two circles may overlap (touching is allowed).
"""

from itertools import combinations

from ..exact import ExactnessError, fmt, to_fraction
from ..model import Result

KIND = "max"


def verify(sub, spec):
    n = spec["n"]
    circles = sub.solution.get("circles")
    if not isinstance(circles, list):
        return Result(False, error="solution.circles must be a list of [x, y, r] rows")
    if len(circles) != n:
        return Result(False, error=f"expected exactly {n} circles, got {len(circles)}")
    rows = []
    for i, c in enumerate(circles):
        if not isinstance(c, list) or len(c) != 3:
            return Result(False, error=f"circle {i}: expected [x, y, r]")
        try:
            x, y, r = (to_fraction(v) for v in c)
        except ExactnessError as exc:
            return Result(False, error=f"circle {i}: {exc}")
        if r <= 0:
            return Result(False, error=f"circle {i}: radius must be positive")
        if x - r < 0 or x + r > 1 or y - r < 0 or y + r > 1:
            return Result(False, error=f"circle {i} is not inside the unit square")
        rows.append((x, y, r))
    for (i, (xi, yi, ri)), (j, (xj, yj, rj)) in combinations(enumerate(rows), 2):
        dx, dy, s = xi - xj, yi - yj, ri + rj
        if dx * dx + dy * dy < s * s:
            return Result(False, error=f"circles {i} and {j} overlap")
    score = sum(r for _, _, r in rows)
    return Result(True, score=score, score_text=fmt(score, 12),
                  details=[f"{n} circles inside the unit square, no overlaps (exact arithmetic)"])
