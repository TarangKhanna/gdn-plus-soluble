"""Constant-gate repair of the frozen whole-network wreath certificate.
Only the U2 Q/K/V construction changes; original frozen modules remain intact.
"""
import argparse,hashlib,importlib,json,resource,signal,time
from pathlib import Path

def repaired_prefix(b,fp,labels):
    D,M,HD,WORK,SH=b.D,b.M,b.HD,b.WORK,b.SH
    outlabels=tuple((f,B,p,n) for f in b.product(range(3),repeat=3) for B in range(2) for p in range(2) for n in range(3))
    index={t:i for i,t in enumerate(outlabels)}
    keys=[[D*int(t[0][3]==0),D*int(t[0][3]!=0)] for t in labels]
    queries=[[0,D] for _ in labels]
    values=[[D*int(t[0][3]==n) for n in (1,2)] for t in labels]
    main=b.Head(fp,b.projection(fp,labels,keys),b.projection(fp,labels,queries),b.projection(fp,labels,values))
    assert main.B is None
    comp=b.overwrite_head(fp,labels,[[D] for _ in labels])
    O=[[] for _ in range(M)]
    O[WORK]=[(0,-D//2),(1,-D//2),(HD,D//2)]
    O[WORK+2]=[(0,D//2)];O[WORK+4]=[(1,D//2)]
    for j in range(3):O[WORK+2*j+1]=[(i,-w) for i,w in O[WORK+2*j]]
    O[SH]=[(HD,-D//2)];O[SH+1]=[(HD,D//2)]
    amp=b.R*D if hasattr(b,'R') else D//2
    ff=b.build_joint(fp,labels,3,lambda c:[amp*int(j==c) for j in range(3)],lambda l,n:index[(labels[l][0][:3],labels[l][1],labels[l][2],n)])
    if hasattr(b,'SCALE'):O=[[(i,b.SCALE*w) for i,w in row] for row in O]
    return b.Layer(fp,labels,[main,comp],b.Mat(fp,O,2*HD),ff,outlabels)

def main():
    a=argparse.ArgumentParser();a.add_argument('convention',choices=['unit','variance']);a=a.parse_args()
    module='independent_wreath_unit_keys' if a.convention=='unit' else 'independent_wreath_variance'
    b=importlib.import_module(module)
    b.prefix=lambda fp,labels:repaired_prefix(b,fp,labels)
    start=time.perf_counter();cpu=time.process_time();fp=b.FP();net=b.Network(fp)
    for layer in net.layers:
        for head in layer.heads:assert head.B is None,'token-dependent beta remains'
    result=b.exhaustive(net)
    assert result['states']==5104 and result['edges']==413424
    assert not fp.overflow
    result.update(status='PASS',convention=a.convention,constant_alpha_beta=1,token_dependent_gates=False,reset_inert_row='row0 zero by induction; row1 is old reset state',D=b.D,p=b.P,width=b.M,layers=7,heads_per_layer=2,ff_width=b.FF_WIDTH,input_alphabet=81,output_alphabet=81,norm_calls=fp.norm_calls,scalar_operations=fp.operations,absorbing_overflow=fp.overflow,cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,max_parameter_numerator=fp.max_parameter,max_pre_round_numerator=f'{fp.max_pre_n}/{fp.max_pre_d}')
    root=Path(__file__).parent
    result['source_hashes']={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in ['gate_repair_certificate.py',module+'.py']}
    out=root/'evidence'/('gate-repair-'+a.convention+'-result.json');out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,sort_keys=True))

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('90-second wall limit')));signal.alarm(90)
    main()
