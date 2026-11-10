"""Run the portable certificates and check their machine-readable results.

Run in a fresh copy for release verification. No models or third-party Python
packages are used. Recorded runtime and memory are specific to the host.
"""

import hashlib
import json
import platform
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> dict:
    return json.loads((ROOT / "_verified/evidence" / name).read_text())


def main() -> None:
    if sys.flags.optimize:
        raise SystemExit("Run without -O: the certificates require invariant assertions.")
    started = time.monotonic()
    provenance = json.loads((ROOT / "PROVENANCE.json").read_text())
    for name, expected in provenance["current_first_party_sources"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    commands = []
    for name in ("rescaling.py", "general_phase.py", "z3_network.py", "z3_wr_u2.py", "sensitivity.py", "rank_one_sensitivity.py", "interface_example.py"):
        command = [sys.executable, "-B", str(ROOT / "certs" / name)]
        subprocess.run(command, cwd=ROOT, check=True)
        commands.append(["python3", "-B", "certs/" + name])
    for arm, maximum in (("unit", 1524096), ("variance", 9144576)):
        z3 = load("task1-" + arm + "-result.json")
        baseline = z3["baseline"]
        assert z3["status"] == baseline["status"] == "PASS"
        assert (baseline["states"], baseline["edges"], baseline["normalization_calls"]) == (13, 39, 390)
        assert baseline["max_mean_deviation_numerator"] == baseline["max_squared_norm_deviation_numerator_squared"] == 0
        metrics = z3["baseline_metrics"]
        assert not metrics["absorbing_overflow"]
        assert Fraction(metrics["max_pre_round_numerator"]) == maximum
        streams = z3["C3"]
        assert (streams["short_nonempty_sequences"], streams["short_positions_checked"], streams["long_sequences"], streams["long_positions_checked"]) == (9840, 73812, 200, 538724)
        for mode in ("ties_even", "floor_sqrt"):
            assert z3["C7"][mode]["status"] == "PASS"
        fused = z3["C7"]["fused_exact"]
        assert fused["status"] == "FAIL" and fused["earliest_word"] == [0, 0]
        assert fused["earliest_error"] == "marker canonical mismatch"
        wreath = load("gate-repair-" + arm + "-result.json")
        assert wreath["status"] == "PASS" and not wreath["absorbing_overflow"]
        assert (wreath["states"], wreath["edges"], wreath["norm_calls"]) == (5104, 413424, 22977)
        assert wreath["constant_alpha_beta"] == 1 and not wreath["token_dependent_gates"]
    rank_one = load("rank-one-sensitivity-result.json")
    assert rank_one["status"] == "PASS" and rank_one["reported_witness_reproduced"]
    assert rank_one["complete_network_runs"] == 12 and len(rank_one["cases"]) == 6
    assert all(c["complete_output_differs"] for c in rank_one["cases"])
    assert load("interface-example-result.json")["status"] == "PASS"
    assert load("rescaling-result.json")["cases"] == 20450
    assert load("general-phase-result.json")["phase_pairs"] == 818
    assert load("brief-p21-witness-result.json")["status"] == "EXPECTED_FAIL"
    assert load("review-claim-checks-result.json")["tie_away_marker"]["not_stationary"]
    result = {"status": "PASS", "python": platform.python_version(), "platform": platform.system(),
              "resource_units_note": "Frozen ru_maxrss fields use host units: bytes on macOS, KiB on Linux; not compared as scientific results.",
              "commands": commands, "wall_seconds": time.monotonic() - started,
              "current_sources_match_provenance": True,
              "expected_failures": ["variance p21 parameter range", "fused marker invariant at [0,0]", "ties-away marker stationarity"],
              "scope": "finite network certificates and bounded algebra checks; not a formal proof checker or StateBench identification"}
    (ROOT / "_verified/evidence/release-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
