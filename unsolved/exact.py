"""Exact number handling.

Submissions are JSON. Python's default JSON parser turns 0.1 into a binary float, which
would let rounding decide a record. Here every number is read as the exact decimal (or
fraction) that was written in the file and compared with rational arithmetic.
"""

import json
from decimal import Decimal, InvalidOperation
from fractions import Fraction


class ExactnessError(ValueError):
    """A value could not be read as an exact finite rational number."""


def _reject_constant(name):
    raise ExactnessError(f"non-finite constant {name!r} is not allowed")


def load_json_exact(text):
    """Parse JSON keeping every number exact (decimals as Decimal, integers as int)."""
    return json.loads(text, parse_float=Decimal, parse_int=int, parse_constant=_reject_constant)


def to_fraction(value):
    """Exact rational from an int, Decimal, or a string such as "0.25", "-3/7" or "1e-3"."""
    if isinstance(value, bool):
        raise ExactnessError("booleans are not numbers")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ExactnessError(f"non-finite number {value}")
        return Fraction(value)
    if isinstance(value, str):
        s = value.strip()
        try:
            if "/" in s:
                num, den = s.split("/", 1)
                f = Fraction(int(num), int(den))
            else:
                d = Decimal(s)
                if not d.is_finite():
                    raise ExactnessError(f"non-finite number {value!r}")
                f = Fraction(d)
        except (ValueError, ZeroDivisionError, InvalidOperation) as exc:
            raise ExactnessError(f"cannot read {value!r} as an exact number") from exc
        return f
    if isinstance(value, float):
        raise ExactnessError("binary floats are not accepted; write the number as a decimal literal")
    raise ExactnessError(f"expected a number, got {type(value).__name__}")


def to_int(value):
    """Exact integer (no decimals, no booleans)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExactnessError(f"expected an integer, got {value!r}")
    return value


def fmt(value, digits=12):
    """Human-readable decimal rendering of a Fraction or int."""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        return f"{float(value):.{digits}f}".rstrip("0").rstrip(".")
    return str(value)
