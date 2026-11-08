# State tracking in GDN+: a finite-precision expressivity result

Companion code for **Soluble State Tracking in Materialized Fixed-Point GDN+**,
Tarang Khanna (2026). [Read the paper](https://zenodo.org/records/24057440).

## Why this matters

AI sequence models need to maintain state as updates accumulate—for example,
tracking variables through a sequence of instructions. This project studies
what GDN+, a recurrent sequence-model architecture, can represent with
fixed-size, finite-precision memory.

The paper gives a complete network construction for a broad class of finite-state
computations, including modular counting and compositions with resettable memory.
Formally, it covers every finite soluble monoid. Network width and depth do not
grow with sequence length.

The construction extends StateBench's aperiodic and rounded-parity lower bounds
with general modular counters and full-network composition, under the specified
arithmetic assumptions.

The code supplies complete network parameters, an exact-arithmetic simulator
and exhaustive checks of the construction.

## What is verified

Each reachable internal network configuration is checked against every possible
next input—not just sampled sequences:

| Constructed network | Internal configurations | One-input updates checked |
|---|---:|---:|
| Modulo-3 counter | 13 | 39 |
| Counters composed with resettable memory | 5,104 | 413,424 |

Counts hold for each of the two normalization constructions. Tests also check
normalization, decoding, overflow and arithmetic sensitivity.
[Verification details](VERIFICATION.md) explain the terminology and test scope.

## Reproduce

Python 3.10+ on macOS or Linux; standard library only:

```sh
python3 -B certs/run_all.py
```

Success exits with code 0 and records `"status": "PASS"` in
`_verified/evidence/release-result.json`. Do not use Python `-O`: assertions are
part of the checks, including the documented negative witnesses.

## Scope

The theorem uses **materialized fixed-point arithmetic**: products are rounded
individually before accumulation. Constant endpoint gates, zero initial memory
and specified normalization rules are essential assumptions. This is an existence
result, without an efficient-size guarantee or matching upper bound.

It does not show that trained models learn this mechanism, that production
kernels implement it, or that the model exactly matches StateBench's inherited
execution. Finite certificates support concrete networks; the general theorem
rests on the paper's proof. The preprint is not peer reviewed.

## Provenance and citation

Numerical expressions, assertions and expected results are preserved from the
Zenodo archive. Documentation changes and source hashes are recorded in
`ZENODO_RELEASE.json` and `PROVENANCE.json`.

Large language models contributed to the mathematical constructions,
verification, checking and writing. The human author is responsible for the work.

[Paper and code DOI: 10.5281/zenodo.24057440](https://doi.org/10.5281/zenodo.24057440)
· [Citation metadata](CITATION.cff) · [MIT code license](LICENSE).
The paper is separately licensed under CC BY 4.0.
