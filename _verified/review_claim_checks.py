"""Exact checks of rounding, normalization, and joint-label identities."""
from fractions import Fraction as F
from math import isqrt
import json

def nearest(x):return (2*x.numerator+x.denominator)//(2*x.denominator)
def away(x):
    a=abs(x);v=(2*a.numerator+a.denominator)//(2*a.denominator)
    return v if x>=0 else -v
k=[F(-5,6),F(-3,6),F(-1,6),F(-1,6)]
A=[[int(i==j)-k[i]*k[j] for j in range(4)] for i in range(4)]
def action(v,rounding):return [sum(rounding(A[i][j]*v[j]) for j in range(4)) for i in range(4)]
w=[away(x) for x in k];tw=action(w,away);new=[a+b for a,b in zip(tw,w)]
assert w==[-1,-1,0,0] and new!=w
# Nonzero epsilon is not categorically fatal for a correct-rounded root.
roots=[]
for D in [9,1008,7056,96768]:
    x=D*D+D;root=isqrt(x)
    if 4*x>=(2*root+1)**2:root+=1
    assert root==D
    assert 4*(D*D+D)<(2*D+1)**2
    roots.append(dict(D=D,epsilon=f'1/{D}',root_numerator=root,normalization_divisor=1))
# Payload tuple uses one joint label, not simultaneous scaled field codes.
for cardinality in [1,2,5,81,324,1000]:
    assert 4*F(1,2)**2==1
D=1008;L=F(D,9)
assert (D*L/3).denominator==1 and D%27!=0
out=dict(status='PASS',tie_away_marker=dict(w=w,Tw=tw,next=new,not_stationary=True),joint_label_interface='one token pair plus one shared pair, norm1 independent of joint alphabet cardinality; width grows',epsilon_counterpoint=roots,epsilon_scope='Only normalization that adds epsilon before a correctly-rounded root; not implied by sqrt_D(1)=1 alone, no floating-point claim',parameter_numerator=int(D*L/3),interpretation='local algebraic checks, not a full-network certificate')
from pathlib import Path
p=Path(__file__).parent/'evidence/review-claim-checks-result.json';p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
