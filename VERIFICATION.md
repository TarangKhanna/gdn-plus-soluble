# Understanding the verification results

## What the task names mean

**Z3 (modulo 3)** is a counter whose answer cycles through 0, 1 and 2. For example,
adding 1 three times returns to 0. It is a simple periodic computation: the model
must retain the correct phase across arbitrarily many updates.

**Z3 wreath U2** composes counters with a resettable lower-state memory. Its upper
updates depend on the previous lower state. This tests whether complete network
components can pass the right information between layers, including across reset
operations. The wreath-product notation names that composition; this is more
than a second standalone counter.

## States and transitions

A **reachable state** here is a distinct internal configuration of the complete
constructed neural network, including its recurrent memories and initialization
bookkeeping. It is not a hidden-unit count, parameter count or output-label count.
The modulo-3 network has three possible answers but 13 reachable internal states.

A **transition** is the update produced by one legal next input from one such
configuration. The verifier checks all of them:

| Network | Configurations | Input choices per configuration | Transitions |
|---|---:|---:|---:|
| Z3 | 13 | 3 | 39 |
| Z3 wreath U2 | 5,104 | 81 | 413,424 |

These counts apply separately to both normalization constructions. Exhaustive
closure of the represented finite transition system supports all input lengths
for these concrete networks, provided the implementation and state encoding
faithfully model all relevant mutable state. It does not replace the algebraic
proof for every finite soluble monoid.

## The two normalization conventions

Both first subtract the mean of the vector coordinates (centering).

- **Centered unit Euclidean:** rescale the centered vector to length 1, so the
  sum of squared coordinates is 1.
- **Centered population variance:** rescale so the average squared centered
  coordinate is 1. This is variance-one normalization with no epsilon or affine
  adjustment, as explicitly defined in the paper.

These are separate constructions with different parameter/precision choices,
not a claim that arbitrary software LayerNorm implementations are interchangeable.
The concrete Euclidean construction fits p=21; the variance construction uses p=24.
The insufficient variance p=21 bound is retained as an expected negative witness.

## Other checks

- **Rescaling:** checks that changing the fixed-point grid together with the
  prescribed state/value scaling preserves the counter recurrence.
- **Phase identities for moduli 2–13:** checks the finite algebra behind cyclic
  encodings for counters that wrap after 2 through 13 steps. This is bounded
  support for the general proof, not a test of every modulus.
- **Width-28 diagram and (1,1,2) example:** checks that the paper's residual-vector
  coordinate layout matches the concrete Euclidean implementation. The example's
  running modulo-3 answers are 1, 2 and 1. Width 28 is a coordinate count, not depth.
- **Short/long replay:** checks sequences by following previously verified
  transitions. Memoization means an already evaluated state/input update is
  reused, so replay positions are not extra independent matrix evaluations.
- **Arithmetic sensitivity:** changes rounding or update evaluation rules. The
  fused-exact witness fails a marker invariant; ties-away rounding breaks marker
  stationarity. Neither is claimed to demonstrate an incorrect final answer.
- **Complete-output rank-one sensitivity:** `certs/rank_one_sensitivity.py`
  evaluates both complete networks on three words from zero initial memory.
  It computes `d = k^T S` using individually rounded products and left-to-right
  checked sums, then `(S[i,j] - round(k[i]*d[j])) + round(k[i]*v[j])`,
  subtracting before adding the write. It does not materialize `I - kk^T`.
  All other operations and assertions stay active. This differs from fused-exact,
  whose recurrence intermediates are exact and whose outputs are cast once.
  Both normalization constructions reproduce the following decoded outputs:

  | Input word | Materialized | Rounded rank-one |
  |---|---|---|
  | `[1,1]` | `[1,2]` | `[1,1]` |
  | `[1,2]` | `[1,0]` | `[1,2]` |
  | `[1,0]` | `[1,1]` | `[1,0]` |

  These are observed complete outputs, not conclusions drawn from a failed
  marker invariant. The certificate records 12 complete network runs.

The suite includes rescaling, phase identities, complete networks, the worked
example and sensitivity checks. Run `python3 -B certs/run_all.py` from the root.
No weights, training or network access are needed.

## Files and result interpretation

`certs/` contains the entry points. `_verified/` contains numerical implementations;
`sim/fp.py` re-exports their arithmetic class, rather than implementing another
independent simulator. `expected/` preserves the published reference outputs and adds the new
`rank-one-sensitivity-result.json` reference.

Runtime, memory, Python versions, source hashes and traceback line numbers may
vary after the documented source changes or across machines. Compare scientific
invariants and counts, rather than requiring byte-identical generated JSON.
`PROVENANCE.json` pins current sources. `SHA256SUMS` verifies the current checkout;
`ZENODO_SHA256SUMS` is the original manifest for the archived ZIP only.

The universal theorem, arithmetic definitions, prior-work comparison and full
proof are in the [paper](https://doi.org/10.5281/zenodo.24057440). These certificates
are not a proof assistant, a learned-model experiment or a production-kernel test.
