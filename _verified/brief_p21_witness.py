"""Check the p=21 parameter-range counterexample for the variance-normalized network."""
import json
from pathlib import Path
import independent_variance as v
# The requested datatype limit is changed, not the architecture/parameters.
v.LIMIT=2**21
fp=v.Fixed()
try:
    v.MarkerLayer(fp)
except OverflowError as exc:
    out=dict(status='EXPECTED_FAIL',literal_task1_C5='FAIL',reason='variance marker parameters exceed p21 before any token',requested_p=21,limit=2**21,overflow_witness=str(exc),absorbing_overflow=fp.overflow,prior_verified_p=24,construction_unchanged=True)
else:
    raise AssertionError('expected p21 failure was absent')
p=Path(__file__).parent/'evidence'/'brief-p21-witness-result.json';p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
