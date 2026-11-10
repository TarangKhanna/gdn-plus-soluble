
# GDN+ State Tracking: What Can Fixed-Size Neural Memory Compute?

**Independent AI research · Recurrent sequence models · State tracking · Neural-network expressivity**

Can a recurrent neural network reliably maintain and update structured information over arbitrarily long sequences without increasing its memory size?

This repository investigates that question for **Gated DeltaNet (GDN+)**, a recurrent neural-network architecture relevant to efficient sequence modeling.

> **Main result:** Under a precisely specified materialized fixed-point arithmetic model, GDN+ networks can represent **every finite soluble state-tracking computation**, including modular counting and compositions of interacting state machines. For each fixed task, network width and depth remain independent of sequence length.
>
> The result is constructive: the repository provides explicit network parameters, an exact-arithmetic simulator, and exhaustive verification of up to **413,424 state transitions** per normalization construction.

**[Read the paper](https://doi.org/10.5281/zenodo.24057440)** · **[Verification details](VERIFICATION.md)** · **[Reproduce the results](#reproducing-the-results)**

*Companion code for "Soluble State Tracking in Materialized Fixed-Point GDN+" — Tarang Khanna (2026). Research preprint, not yet peer reviewed.*

---

## Why This Matters for AI

Modern sequence models must maintain information as new inputs arrive. Examples include:

- Tracking variables through long sequences of instructions.
- Maintaining counters, modes, and other structured state.
- Applying updates whose effects depend on previous states.
- Combining multiple interacting memory operations.

Recurrent architectures offer an alternative to storing or attending over the entire input history. But their computational capabilities depend on the kinds of state transitions their recurrent updates can represent.

**A key question is whether restricted recurrent networks can implement periodic and compositional state tracking, rather than only simpler memory operations.**

### Example: Modular Counting

Consider a model processing a sequence of increment instructions while tracking a counter modulo 3.

```text
Input:       +1   +1   +1   +1   +1
State:        1    2    0    1    2
```

The counter must preserve the correct phase regardless of sequence length.

This is not automatically possible for every recurrent architecture. Under exact arithmetic, certain restricted linear recurrent dynamics cannot maintain arbitrary periodic state transitions.

However, **finite-precision rounding changes the computational behavior**.

This work constructs bounded modular counters using individually rounded matrix products, then shows how to combine those counters with other state-tracking components.

The important advance is not merely counting modulo 3. It is constructing **arbitrary fixed-modulus counters and composable state machines within a complete neural-network architecture**.

---

## What Was Previously Known?

Ai2's [StateBench research](https://arxiv.org/abs/2611.03094), by Petty, Merrill, and Sabharwal (2026), studies a hierarchy of state-tracking computations.

The hierarchy includes:

```text
R-trivial
    ⊊
Aperiodic
    ⊊
Soluble
    ⊊
All finite monoids
```

StateBench established that fixed-precision Gated DeltaNet with nonnegative-eigenvalue updates could represent every **aperiodic** state-tracking task.

It also demonstrated a particular periodic computation—parity—enabled by finite-precision rounding.

However, the paper left open whether this architecture could express the entire **soluble** class, which includes arbitrary finite cyclic counting and compositions with resettable memory.

### What This Work Adds

This paper constructs networks for **every finite soluble monoid** under an explicitly defined materialized fixed-point GDN+ model.

The construction supplies three key mechanisms:

**1. General modular counters**

Individually rounded matrix products implement bounded counters modulo any fixed integer, extending beyond parity.

**2. Normalization-compatible state representations**

Cyclically shifted counters produce constant-norm representations that survive the network's normalization and residual operations. Finite feedforward selectors decode these representations into reusable state labels.

**3. Composition of state machines**

A parity-controlled buffer exposes the previous lower-level state required for composing interacting state machines. Together with payload-preserving recoding, this supports a constructive algebraic induction over finite soluble monoids.

The result is a complete-network construction, not merely an isolated recurrent-head example.

### The Main Theoretical Result

For every finite soluble monoid, there exists a GDN+ network with:

- Fixed finite width and depth for that task.
- Zero-initialized recurrent memory.
- No beginning-of-sequence token.
- No biases or positional inputs.
- Explicitly specified constant endpoint gates.
- A fixed materialized rational-grid arithmetic model.

The network computes the correct prefix state for arbitrarily long nonempty input sequences.

**Important qualification:** The theorem applies to the operational model defined in the paper. Equivalence to all execution details inherited by StateBench, or to production Gated DeltaNet kernels, is not established.

---

## Reproducible Verification

The repository includes explicit constructed networks and an exact-arithmetic verification suite.

Rather than checking only randomly sampled sequences, the verifier enumerates every legal next-input transition from every reachable internal configuration of the constructed networks.

| Constructed network | Reachable configurations | Verified transitions |
|---|---:|---:|
| Modulo-3 counter | 13 | 39 |
| Counter composed with resettable memory | 5,104 | 413,424 |

These counts apply separately to each of two normalization constructions.

The suite also checks:

- State initialization and decoding.
- Layer normalization and residual interfaces.
- Arithmetic overflow and rescaling.
- Modular phase identities.
- Sensitivity to rounding and operation ordering.

The numerical certificates verify concrete network constructions. **The general theorem for all finite soluble monoids follows from the mathematical proof, not from finite enumeration alone.**

[Read the detailed verification guide](VERIFICATION.md).

---

## Reproducing the Results

**Requirements:** Python 3.10+ on macOS or Linux. Standard library only.

No model downloads, GPU, training, or network access are required.

From the repository root:

```bash
python3 -B certs/run_all.py
```

A successful run exits with code 0 and records `"status": "PASS"` in:

```text
_verified/evidence/release-result.json
```

Do not use Python's `-O` flag. Assertions are part of the verification suite, including documented negative witnesses.

---

## Implications for Neural Network Research

### 1. Numerical Arithmetic Can Change Expressivity

Finite precision is often treated as an implementation detail.

This construction demonstrates that, under a particular arithmetic program, rounding can enable recurrent state transitions that are unavailable under corresponding exact-arithmetic restrictions.

**The order in which operations are rounded and materialized can matter to what a neural architecture can represent.**

### 2. Nonnegative-Eigenvalue Updates Do Not Tell the Whole Story

Restrictions on the unrounded recurrent update do not, by themselves, determine the computational capabilities of its finite-precision implementation.

The rounded transition is a nonlinear state update, even when the underlying unrounded matrix has nonnegative eigenvalues.

### 3. Composition Matters More Than Isolated Counting

A model that implements a counter does not automatically support complex state tracking.

The construction demonstrates how state representations, normalization, timing, and decoding can be made compatible so that simpler computations can be composed.

This is important for understanding the theoretical capabilities of recurrent sequence architectures.

### 4. Representability Is Not Learnability

The theorem does **not** establish that gradient-based training will discover these mechanisms.

Important open empirical questions include:

- Can trained recurrent models learn these periodic and composed state updates?
- Do learned solutions generalize to substantially longer sequences?
- How sensitive are the mechanisms to precision, normalization, and execution order?
- Can more efficient constructions achieve comparable capabilities?

These are research directions, not experimental findings reported by this project.

---

## Scope and Limitations

The result assumes **materialized fixed-point arithmetic**, where individual scalar products are rounded before accumulation.

It also depends on the specified normalization rules, constant endpoint gates, and zero initial memory.

This is an expressivity result, not an efficient-size guarantee or matching upper bound.

It does not demonstrate:

- Improved language-model accuracy or reasoning performance.
- Successful training of the constructed networks.
- Equivalence to floating-point or fused production kernels.
- Robustness to arbitrary numerical perturbations.
- Improved long-context benchmark performance.

The distinction between the paper's explicit arithmetic model and practical implementations is essential to interpreting the result.

---

## Research Artifacts and Provenance

The repository preserves the numerical constructions, assertions, and expected results from the published Zenodo code archive.

- [`VERIFICATION.md`](VERIFICATION.md) — Verification methodology and result interpretation.
- [`ZENODO_RELEASE.json`](ZENODO_RELEASE.json) — Archived release metadata and source comparisons.
- [`PROVENANCE.json`](PROVENANCE.json) — Source provenance and scientific scope.
- [`SHA256SUMS`](SHA256SUMS) — Checksums for the repository snapshot.
- [`CITATION.cff`](CITATION.cff) — Citation metadata.

Large language models contributed to developing mathematical constructions, implementing verification, checking arguments, and preparing the manuscript. The author is responsible for the research claims and released materials.

## Citation

**Tarang Khanna (2026).** *Soluble State Tracking in Materialized Fixed-Point GDN+.*

[Paper and code DOI: 10.5281/zenodo.24057440](https://doi.org/10.5281/zenodo.24057440)

Code and repository documentation: MIT License. Paper: CC BY 4.0.
