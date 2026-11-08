"""Retain the parameter-range and marker tie-rule counterexamples."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for name in ("brief_p21_witness.py", "review_claim_checks.py"):
        subprocess.run([sys.executable, "-B", str(root / "_verified" / name)], check=True)
