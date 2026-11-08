"""Independent finite support for the arbitrary-fixed-modulus constant-norm proof.
No rerun of the completed head recurrence; exact phase, carrier and decoder facts.
"""
from fractions import Fraction as F
from math import lcm
from pathlib import Path
import hashlib,json,resource,signal,time
resource.setrlimit(resource.RLIMIT_CPU,(3,3));signal.alarm(5)
start=time.perf_counter()
def center(m,r):return r+m*((-2*r+m)//(2*m))
rows=[]
for m in range(2,14):
    phase=[tuple(center(m,s+j) for j in range(m)) for s in range(m)]
    H=sum(x*x for x in phase[0]);assert len(set(phase))==m
    assert all(F(-m,2)<x<=F(m,2) for p in phase for x in p)
    M=max(m*m,6*m+4)
    L=144*M*(H+1)**2;D=L*m*m
    assert D%36==0 and D%(4*M*(H+1)**2)==0
    for p in phase:
        private=[F(x,H+1) for x in p]+[F(-x,H+1) for x in p]
        private += [F(H-1,2*(H+1)),F(1-H,2*(H+1))]
        assert sum(private)==0 and sum(x*x for x in private)==F(1,2)
        for x in private+[F(1,2),F(-1,2)]:
            assert (D*x).denominator==1
            assert (D*x*x).denominator==1
            assert (D*x/M).denominator==1
    pairs=indicators=induction=0
    for s in range(m):
        for t in range(m):
            dot=sum(x*y for x,y in zip(phase[s],phase[t]))
            assert dot==H if s==t else dot<=H-1
            for same_label in (0,1):
                J=max(0,dot+same_label-H)
                assert J==int(s==t and same_label==1);indicators+=1
            pairs+=1
        for previous_a in range(m):
            # Inductive previous raw row r_j=a_prev+c_m(s_prev+j).
            # Recentering recovers the new exclusive phase, including even ties.
            got=tuple(center(m,previous_a+x) for x in phase[s])
            assert got==phase[(s+previous_a)%m]
            induction+=1
    # General variance-one embedding with a permanent exact+1 coordinate.
    r=m+3;n=4*r*r
    assert 4*m+2*(r*r-1)+2+(2*m+2)<=n
    token_private=F(2)+2*(r*r-1);shared=2*r*r
    assert token_private==shared and token_private+shared==n
    for p in phase:
        ys=[F(2*r*x,H+1) for x in p]+[F(-2*r*x,H+1) for x in p]
        ys += [F(r*(H-1),H+1),F(-r*(H-1),H+1)]
        assert sum(v*v for v in ys)==F(n,2)
        assert token_private+sum(v*v for v in ys)==n
    # Clear actual rational means/squares/variances rather than an unproved
    # minimal denominator formula. State precision then scales consistently.
    denominators=[36,m*m,n,4]
    for p in phase:
        for x in [F(1),F(-1),F(r),F(-r)]+ys:
            denominators += [x.denominator,(x*x).denominator,
                             (x/n).denominator,(x*x/n).denominator]
    DV=lcm(*denominators)*m*m
    assert DV%(m*m)==0
    rows.append(dict(m=m,H=H,unit_width=M,unit_D=D,phase_pairs=pairs,
                     selector_cases=indicators,inductive_phase_cases=induction,
                     variance_width=n,variance_denominator_witness=DV))
print('PASS818 phase pairs,1636 exact joint selectors,818 inductive phase cases for m2..13')
print('PASS unit/private norm identities, even ties and sufficient common-grid witnesses under both conventions')
print(json.dumps(dict(rows=rows,scope='finite support for stated general proof, not a substitute for induction/KR',
                     phase_pairs=sum(x['phase_pairs'] for x in rows),
                     wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time(),
                     script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),sort_keys=True))
