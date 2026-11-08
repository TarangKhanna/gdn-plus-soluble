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
