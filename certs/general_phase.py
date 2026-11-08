"""Check exact phase, carrier and selector identities for moduli 2 through 13."""

import json
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-B", str(root / "_verified/general_phase_check.py")],
        check=True, text=True, capture_output=True,
    )
    print(completed.stdout, end="")
    result = json.loads(completed.stdout.splitlines()[-1])
    assert result["phase_pairs"] == 818
    output = root / "_verified/evidence/general-phase-result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
