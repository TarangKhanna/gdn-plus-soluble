"""Verify the directly implemented constant-gate whole-network wreath construction.
The historical filename is retained for command and result compatibility.
"""
import argparse,hashlib,importlib,json,resource,signal,time
from pathlib import Path

def main():
    a=argparse.ArgumentParser();a.add_argument('convention',choices=['unit','variance']);a=a.parse_args()
    module='independent_wreath_unit_keys' if a.convention=='unit' else 'independent_wreath_variance'
    b=importlib.import_module(module)
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
