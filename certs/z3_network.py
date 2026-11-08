"""Check the complete modulo-3 network under both normalization conventions."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--arm",
        choices=("unit", "variance", "both"),
        default="both",
        help="normalization convention to verify (default: both)",
    )
    args = parser.parse_args()
    arms = ("unit", "variance") if args.arm == "both" else (args.arm,)
    certificate = ROOT / "_verified" / "task1_remaining_checks.py"

    for arm in arms:
        subprocess.run([sys.executable, "-B", str(certificate), arm], check=True)


if __name__ == "__main__":
    main()
