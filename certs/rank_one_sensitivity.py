"""Decode complete networks with materialized and rounded rank-one updates.

For alpha=beta=1, rank-one evaluation computes d = k^T S first, then
S'[i,j] = (S[i,j] - k[i]*d[j]) + k[i]*v[j]. Each multiplication rounds
individually; each sum is accumulated left to right with checked FP additions.
Subtraction precedes the write addition. A = I - kk^T is never materialized.
This is distinct from task1_remaining_checks.fused (exact intermediates and a
single output cast). Q/K/V, readout, normalization and FF remain unchanged.
"""

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_verified"))


def rank_one(fp, state, k, v):
    dots = [fp.dot(list(enumerate(k)), [row[j] for row in state])
            for j in range(len(v))]
    return [[fp.add(fp.add(state[i][j], -fp.mul(k[i], dots[j])),
                    fp.mul(k[i], v[j])) for j in range(len(v))]
            for i in range(len(k))]


def evaluate(b, word, update):
    original = b.materialized
    b.materialized = update
    try:
        fp = b.Fixed()
        network = b.Module(fp)
        outputs = []
        for token in word:
            residual, trace = network.step(b.canonical(token))
            decoded = trace["cyclic"]["decoded"]
            assert residual == b.canonical(decoded)
            outputs.append(decoded)
        assert not fp.overflow
        return dict(decoded=outputs, absorbing_overflow=fp.overflow,
                    normalization_calls=fp.norm_calls,
                    max_pre_round_numerator=str(fp.max_intermediate))
    finally:
        b.materialized = original


def main():
    if sys.flags.optimize:
        raise SystemExit("Run without -O: the certificates require assertions.")
    cases = []
    for arm, module in (("unit", "independent_constant_norm"),
                        ("variance", "independent_variance")):
        b = importlib.import_module(module)
        for word in ([1, 1], [1, 2], [1, 0]):
            baseline = evaluate(b, word, b.materialized)
            alternative = evaluate(b, word, rank_one)
            expected = [1, (1 + word[1]) % 3]
            assert baseline["decoded"] == expected
            # These are measured complete outputs, not an invariant-failure proxy.
            assert alternative["decoded"] == [1, word[1]]
            cases.append(dict(arm=arm, word=word, materialized=baseline,
                              rank_one=alternative,
                              complete_output_differs=baseline["decoded"] != alternative["decoded"]))
    result = dict(status="PASS", cases=cases, complete_network_runs=12,
                  reported_witness_reproduced=all(
                      c["materialized"]["decoded"] == [1, 2] and
                      c["rank_one"]["decoded"] == [1, 1]
                      for c in cases if c["word"] == [1, 1]),
                  operation_order=__doc__)
    out = ROOT / "_verified/evidence/rank-one-sensitivity-result.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
