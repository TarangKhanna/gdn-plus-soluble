# v2 default-branch integration

Integrate the published v2 code and `paper/` directory from publication commit
`d734263692dc29f77f76265198237e23ba963a9e`, retaining the default branch's README
exposition. Update paper links, clone/checkout instructions, citation metadata
and current checksums to identify Zenodo v2, DOI `10.5281/zenodo.24159117`.
Numerical Python and all published manuscript/archive bytes remain unchanged
from the verified v2 snapshots. Original v1 provenance and expected results
are preserved.

## Publication candidate history

Final review corrections narrow the abstract to the reported rounded rank-one
sensitivity and fix the bracketed Nowak citation. Versioned PDF pinpoint checks
are recorded in `paper/CITATION_VERIFICATION.txt`. Numerical Python is unchanged.

The `paper/` directory adds the revised manuscript, PDF, source package and
Appendix D coverage audit. Numerical Python sources are unchanged from
`b4c080f9115598af59d0e0543ee7fbb704283e08`; the final clean suite passed all seven entry points.

Based on immutable published commit `871536d6037326b5ddf222763a4c58d6e7e3f646`.
The published `v0.3-zenodo` tag and all original expected outputs and archived
provenance are preserved.

- Add `certs/rank_one_sensitivity.py` and its expected JSON: 12 complete network
  runs across both normalization constructions. The reported `[1,1]` witness
  reproduces: materialized `[1,2]`, rounded rank-one `[1,1]`. For `[1,2]`, outputs
  are `[1,0]` versus `[1,2]`; for `[1,0]`, `[1,1]` versus `[1,0]`. No discrepancy
  from the reported witness. Individually rounded rank-one evaluation is defined
  in the certificate and is distinct from fused-exact evaluation.
- Move the existing repair's two-row constant-gate prefix directly into
  `independent_wreath_unit_keys.py` and `independent_wreath_variance.py`.
  Identity writes zero to inert row 0; fixed query row 1 reads the retained reset
  state. Remove the runtime replacement from `gate_repair_certificate.py`, keeping
  its command, output names, all gate checks and exhaustive assertions. The older
  `independent_wreath.py` is historical and unchanged; it is not the suite entry.
- Integrate the new certificate in `certs/run_all.py`; verify current source hashes
  instead of claiming the edited sources are unchanged. Preserve v1 source hashes
  in `PROVENANCE.json`, pin all current Python sources, and refresh `SHA256SUMS`.
- Update README and verification notes with the immutable baseline, measured
  outputs, exact command and tested environment: macOS, Python 3.14.4. This revision
  has no new Linux or Python 3.10 verification.

Existing scientific results remain unchanged: per arm, Z3 has 13 states / 39
transitions; Z3 wreath U2 has 5,104 / 413,424. Normalization, overflow, operation
counts and negative witnesses are preserved. Source hashes change legitimately
because the implementation is now direct; runtime/memory also vary by host.
No scientific assertions are relaxed. Original archived provenance below describes
v1, not an executable-AST identity claim for v2.

# v0.3-zenodo

Companion repository snapshot for [Soluble State Tracking in Materialized
Fixed-Point GDN+](https://doi.org/10.5281/zenodo.24057440), published as a
Zenodo preprint on 9 November 2026.

The numerical source, assertions and expected results come from the 36-file
published code archive. Seven module docstrings remove obsolete instructions or redundant provenance wording;
the executable ASTs are unchanged. The README and citation metadata are updated,
with file-level provenance and checksum manifests. No new scientific result,
training claim or production-kernel claim is introduced.

Run `python3 -B certs/run_all.py` from a fresh extraction. Expected reachable
state/transition counts per normalization arm are 13/39 for modulo 3 and
5,104/413,424 for Z3 wreath U2. Overflow, normalization and sensitivity checks
are included. Finite certificates support the concrete networks; the universal
theorem is the paper's algebraic argument.

Code and documentation: MIT. Paper: CC BY 4.0. Substantial language-model
assistance is disclosed in the paper and README. No additional DOI is created.
