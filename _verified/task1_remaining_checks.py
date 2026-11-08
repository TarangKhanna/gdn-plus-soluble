"""Reachable-state, stream, and rounding-sensitivity checks of the fixed network implementations.
The only operator replacements are explicitly labelled sensitivity arms.
C3 replays previously evaluated exact full-network transitions (memoization).
"""
from pathlib import Path
from fractions import Fraction
from itertools import product
from math import isqrt
import argparse,hashlib,importlib,json,platform,random,resource,signal,time,traceback

SEED=20261108

def freeze(x):return tuple(tuple(r) for r in x)
def thaw(x):return [list(r) for r in x]

def floor_norm(fp,b,v):
    D=b.D;n=b.WIDTH
    assert len(v)==n
    total=0;mean_products=0
    for x in v:
        total=fp.add(total,x);mean_products=fp.add(mean_products,fp.mul(x,D//n))
    mean=fp.round(total,n,'mean sum/n');assert mean==mean_products==0
    z=[fp.add(x,-mean) for x in v];ss=0;vp=0
    for x in z:
        square=fp.mul(x,x);ss=fp.add(ss,square)
        if b.WIDTH==36:
            assert x*x%D==0 and square*(D//n)%D==0
            vp=fp.add(vp,fp.mul(square,D//n))
    if b.WIDTH==36:
        assert ss==n*D
        stat=fp.round(ss,n,'variance sumsq/n');assert stat==vp==D
    else:assert ss==D;stat=ss
    root=isqrt(stat*D) # sensitivity: floor, not nearest
    fp.check(root,operation='floored sqrt');assert root==D
    out=[fp.round(x*D,root,'normalization division') for x in z]
    fp.norm_calls+=1;assert out==v
    return out

def fused(fp,b,state,k,v):
    # Exact rank-one affine recurrence, rounded once per output coordinate.
    # Unlike the baseline, neither A nor individual recurrence products round.
    D=b.D;n=len(k)
    def check(x):fp.check(x.numerator,x.denominator,operation='exact fused intermediate');return x
    dot=[]
    for j in range(len(v)):
        s=Fraction(0)
        for t in range(n):s=check(s+check(Fraction(k[t]*state[t][j],D)))
        dot.append(s)
    out=[]
    for i in range(n):
        row=[]
        for j in range(len(v)):
            correction=check(Fraction(k[i],D)*dot[j]);write=check(Fraction(k[i]*v[j],D))
            value=check(check(Fraction(state[i][j])-correction)+write)
            row.append(fp.round(value.numerator,value.denominator,'single fused output cast'))
        out.append(row)
    return out

def graph(b,mode):
    class Observed(b.Fixed):
        def __init__(self):
            super().__init__();self.max_mean_deviation=0;self.max_sumsq_deviation=0
        def norm(self,v):
            self.max_mean_deviation=max(self.max_mean_deviation,abs(sum(v)))
            target=(b.WIDTH if b.WIDTH==36 else 1)*b.D*b.D
            self.max_sumsq_deviation=max(self.max_sumsq_deviation,abs(sum(x*x for x in v)-target))
            if mode=='floor_sqrt':return floor_norm(self,b,v)
            return super().norm(v)
        def round(self,n,d,operation):
            if mode!='ties_even':return super().round(n,d,operation)
            assert d>0;self.check(n,d,operation);self.operations+=1
            q,r=divmod(n,d);v=q+int(2*r>d or (2*r==d and q%2))
            self.check(v,operation='rounded '+operation);return v
    fp=Observed();module=b.Module(fp)
    original=b.materialized
    if mode=='fused_exact':b.materialized=lambda fp,s,k,v:fused(fp,b,s,k,v)
    zero=(freeze(module.marker.state),freeze(module.cyclic.state),tuple([0]*b.WIDTH),tuple([0]*b.WIDTH))
    states=[zero];seen={zero:0};refs=[0];words=[()];edges=[];pos=0;attempts=0
    try:
        while pos<len(states):
            old=states[pos]
            for a in range(3):
                attempts+=1;word=words[pos]+(a,)
                module.marker.state=thaw(old[0]);module.cyclic.state=thaw(old[1])
                try:
                    mid,m=module.marker.step(b.canonical(a))
                    B=int(old[0]==zero[0]);assert mid==b.canonical(2*a+B),'marker canonical mismatch'
                    out,c=module.cyclic.step(mid);expected=(refs[pos]+a)%3
                    assert c['decoded']==expected,('wrong modulo readout',c['decoded'],expected)
                    assert out==b.canonical(expected),'final canonical mismatch'
                    new=(freeze(module.marker.state),freeze(module.cyclic.state),tuple(mid),tuple(out))
                    if new in seen:
                        nxt=seen[new];assert refs[nxt]==expected,'aliased full physical/residual state'
                    else:
                        nxt=len(states);seen[new]=nxt;states.append(new);refs.append(expected);words.append(word)
                    edges.append((pos,a,nxt,c['decoded']))
                except Exception as exc:
                    return fp,dict(status='FAIL',earliest_word=list(word),earliest_error=str(exc),states_discovered=len(states),transitions_attempted=attempts,successful_edges=len(edges),frontier_exhausted=False,traceback=traceback.format_exc()),None
            pos+=1
        assert fp.max_mean_deviation==0 and fp.max_sumsq_deviation==0
        table={(i,a):(n,d) for i,a,n,d in edges}
        result=dict(status='PASS',states=len(states),edges=len(edges),frontier_exhausted=True,marker_states=len({x[0] for x in states}),cyclic_states=len({x[1] for x in states}),joint_state_includes='all marker/cyclic memory entries and both post-layer residual vectors',exact_transition_table=edges,normalization_calls=fp.norm_calls,max_mean_deviation_numerator=fp.max_mean_deviation,max_squared_norm_deviation_numerator_squared=fp.max_sumsq_deviation,canonical_checks='every complete evaluated edge',readout_checks='unique argmax on every complete evaluated edge')
        return fp,result,table
    finally:b.materialized=original

def streams(table):
    digest=hashlib.sha256();short=0;short_positions=0
    def run(word):
        state=0;prefix=0
        for a in word:
            state,decoded=table[state,a];prefix=(prefix+a)%3
            assert decoded==prefix
        return len(word)
    for length in range(1,9):
        for word in product(range(3),repeat=length):short_positions+=run(word);short+=1
    rng=random.Random(SEED);long_positions=0;lengths=[]
    for _ in range(200):
        n=rng.randint(500,5000);word=tuple(rng.randrange(3) for _ in range(n));lengths.append(n)
        digest.update(n.to_bytes(4,'big'));digest.update(bytes(word));long_positions+=run(word)
    return dict(status='PASS',short_nonempty_sequences=short,short_positions_checked=short_positions,lengths=list(range(1,9)),empty_word='excluded: no last-token readout by the theorem convention',long_sequences=200,long_positions_checked=long_positions,long_lengths=lengths,random_seed=SEED,random_input_sha256=digest.hexdigest(),execution='replay of complete FP/matrix-evaluated joint-state transitions; no reference feeds model; every prefix checked')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('arm',choices=['unit','variance']);a=ap.parse_args()
    b=importlib.import_module('independent_constant_norm' if a.arm=='unit' else 'independent_variance')
    start=time.perf_counter();cpu=time.process_time();root=Path(__file__).parent
    result=dict(status='FAIL',arm=a.arm,D=b.D,p=b.P,width=b.WIDTH,amendment='unit normalization uses p=21; variance normalization uses p=24; p=21 variance counterexample retained',rounding_semantics=dict(baseline='nearest ties positive infinity; scalar products individually rounded; materialized A; left-to-right sums',ties_even='nearest ties even for every scalar cast; sqrt nearest ties cannot occur for integral radicand',floor_sqrt='baseline scalar arithmetic, actual square-root output floored',fused_exact='exact rank-one affine recurrence, one cast per state output; QKV/O/LN/FF stay baseline'),python=platform.python_version())
    fp,base,table=graph(b,'baseline');result['baseline']=base
    result['baseline_metrics']=dict(max_parameter_numerator=fp.max_parameter,max_pre_round_numerator=str(fp.max_intermediate),absorbing_overflow=fp.overflow,scalar_operations=fp.operations,normalization_calls=fp.norm_calls)
    if base['status']=='PASS':
        result['C3']=streams(table);result['C7']={}
        for mode in ['ties_even','floor_sqrt','fused_exact']:
            f,r,t=graph(b,mode)
            r['absorbing_overflow']=f.overflow;r['normalization_calls']=f.norm_calls
            if t is not None:r['C3']=streams(t)
            result['C7'][mode]=r
        result['status']='PASS'
    result.update(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    result['source_hashes']={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in [Path(__file__).name,b.__name__+'.py']}
    path=root/'evidence'/('task1-'+a.arm+'-result.json');path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('C3','C7','baseline')},sort_keys=True))
    print(json.dumps(dict(baseline=base['status'],states=base.get('states'),edges=base.get('edges'),C3=result.get('C3',{}).get('status'),C7={k:v['status'] for k,v in result.get('C7',{}).items()})))
    if result['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_CPU,(30,30));signal.alarm(45);main()
