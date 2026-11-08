"""Check scaled materialized counters with exact integer-grid arithmetic."""

import argparse
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def nearest(value: Fraction) -> int:
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def retained(m: int, numerator: int) -> int:
    """One active row after separately rounding all m**2 matrix products."""
    diagonal = nearest(Fraction((m * m - 1) * numerator, m * m))
    off_diagonal = nearest(Fraction(-numerator, m * m))
    return diagonal + (m * m - 1) * off_diagonal


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    cases = 0
    for m in range(2, 14):
        for scale in (1, 2, 3, 4, 36):
            denominator = scale * m * m
            for r in range(-2 * m, 3 * m):
                for a in range(m):
                    # Physical state r/(scale*m) has grid numerator m*r.
                    write = nearest(Fraction(denominator * a, scale * m))
                    got = retained(m, m * r) + write
                    expected = m * (r + a + m * nearest(Fraction(-r, m)))
                    assert got == expected, (m, scale, r, a, got, expected)
                    cases += 1
    # This is a single retained-update witness at a supplied physical state.
    assert retained(3, 6) == -3
    result = {
        "status": "PASS", "cases": cases, "moduli": [2, 13],
        "scales": [1, 2, 3, 4, 36],
        "unscaled_witness": {"m": 3, "D": 18, "old_state": "1/3",
                             "a": 0, "new_state": "-1/6"},
        "scope": "scalar counter identity; full networks checked separately",
    }
    output = ROOT / "_verified" / "evidence" / "rescaling-result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
