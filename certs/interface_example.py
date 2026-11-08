"""Check the paper's worked example and zero-based width-28 coordinate diagram."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_verified"))
import independent_constant_norm as network


def main() -> None:
    if sys.flags.optimize:
        raise SystemExit("Run without -O: the certificate requires assertions.")
    groups = {"token": list(range(12)), "phase": list(range(12, 18)),
              "padding": list(range(18, 22)), "unused": list(range(22, 26)),
              "shared": [26, 27]}
    assert sorted(i for indices in groups.values() for i in indices) == list(range(28))
    fp = network.Fixed()
    module = network.Module(fp)
    expected = [(1, 1, [1, 2, 0], [0, 1, -1], 1),
                (1, 0, [2, 0, 1], [1, -1, 0], 2),
                (2, 0, [1, 2, 3], [-1, 0, 1], 1)]
    rows = []
    previous = None
    for t, (a, bit, raw, phase, residue) in enumerate(expected, 1):
        centered = lambda r: r + 3 * ((-2 * r + 3) // 6)
        algebra = [a + centered(j if previous is None else previous[j]) for j in range(3)]
        assert algebra == raw
        previous = raw
        mid, marker = module.marker.step(network.canonical(a))
        assert mid == network.canonical(2 * a + bit)
        assert marker["read"][0] - 3 * marker["read"][1] == bit
        assert all(not x or i in (12, 13, 14, 15, 26, 27)
                   for i, x in enumerate(marker["write"]))
        out, cyclic = module.cyclic.step(mid)
        assert all(row == cyclic["state"][0] for row in cyclic["state"])
        assert [x // 3 for x in cyclic["state"][0][:3]] == raw
        assert all(x % 3 == 0 for x in cyclic["state"][0][:3])
        assert [r - a for r in raw] == phase
        write = cyclic["write"]
        for j, c in enumerate(phase):
            assert write[12 + 2 * j:14 + 2 * j] == [c * network.D // 4, -c * network.D // 4]
        assert write[18:22] == [network.D // 4, -network.D // 4] * 2
        assert write[22:26] == [0] * 4
        assert write[26:28] == [-network.D // 2, network.D // 2]
        g = [x + y for x, y in zip(mid, write)]
        assert g[26:28] == [0, 0]
        assert sum(g) == 0 and sum(x * x for x in g) == network.D ** 2
        assert out == network.canonical(residue) and cyclic["decoded"] == residue
        rows.append({"t": t, "a": a, "B": bit, "r": raw,
                     "exclusive_phase": phase, "inclusive_residue": residue})
    result = {"status": "PASS", "width": 28, "coordinate_indexing": "zero-based",
              "groups": groups, "marker_workspace": [12, 13, 14, 15],
              "example": rows, "normalization_calls": fp.norm_calls,
              "absorbing_overflow": fp.overflow,
              "frozen_network_sha256": hashlib.sha256((ROOT / "_verified/independent_constant_norm.py").read_bytes()).hexdigest()}
    output = ROOT / "_verified/evidence/interface-example-result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
