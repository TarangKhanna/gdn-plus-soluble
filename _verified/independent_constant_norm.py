"""Independent reconstruction from equations, with strict pre-round FP overflow.
Library-safe: no work or limits at import.
"""
from fractions import Fraction
from math import isqrt
from pathlib import Path
import hashlib,json,resource,signal,time,traceback
D=1008;WIDTH=28;L=112;P=21;LIMIT=2**P
PHASES=((0,1,-1),(1,-1,0),(-1,0,1))

class Fixed:
    def __init__(self):
        self.max_parameter=0;self.max_intermediate=Fraction(0);self.max_operation='';self.operations=0;self.norm_calls=0;self.overflow=False
    def check(self,n,d=1,operation='add'):
        # Overflow is checked on the exact pre-rounded grid numerator n/d.
        # The absorbing error state survives any later exception handling.
        if self.overflow:raise OverflowError('absorbing previous overflow')
        if abs(n)>LIMIT*d:self.overflow=True;raise OverflowError((operation,n,d,LIMIT))
        v=Fraction(abs(n),d)
        if v>self.max_intermediate:self.max_intermediate=v;self.max_operation=operation
        return n
    def round(self,n,d,operation):
        assert d>0;self.check(n,d,operation);self.operations+=1
        v=(2*n+d)//(2*d);self.check(v,operation='rounded '+operation);return v
    def add(self,a,b):self.operations+=1;return self.check(a+b,operation='ordered addition')
    def mul(self,a,b):return self.round(a*b,D,'multiplication')
    def dot(self,row,x):
        s=0
        for i,w in row:s=self.add(s,self.mul(w,x[i]))
        return s
    def mv(self,m,x):return [self.dot(row,x) for row in m]
    def params(self,m):
        for row in m:
            for _,w in row:self.check(w,operation='parameter');self.max_parameter=max(self.max_parameter,abs(w))
        return m
    def norm(self,v):
        assert len(v)==WIDTH
        total=0
        for x in v:total=self.add(total,x)
        mean_direct=self.round(total,WIDTH,'mean sum/n')
        mean_products=0
        for x in v:mean_products=self.add(mean_products,self.mul(x,D//WIDTH))
        assert mean_direct==mean_products==0,('mean',mean_direct,mean_products,v)
        z=[self.add(x,-mean_direct) for x in v]
        squares=0
        for x in z:squares=self.add(squares,self.mul(x,x))
        assert squares==D,('squared norm',squares,v)
        # Rounded square root of represented squares/D, in grid numerators.
        root=isqrt(squares*D)
        if 4*squares*D >= (2*root+1)**2:root+=1
        self.check(root,operation='sqrt');assert root==D
        out=[self.round(x*D,root,'normalization division') for x in z]
        self.norm_calls+=1;assert out==v
        return out

def nz(v):return [(i,x) for i,x in enumerate(v) if x]
def canonical(label):
    v=[0]*WIDTH;v[2*label:2*label+2]=[D//2,-D//2];v[26:28]=[D//2,-D//2];return v

def linear(fp,labels,targets,size):
    return fp.params([[(2*z,2*targets[z][j]) for z in range(labels) if targets[z][j]] for j in range(size)])
def addvec(fp,a,b):return [fp.add(x,y) for x,y in zip(a,b)]
def difference(a,b):return [x-y for x,y in zip(a,b)]
def ff(fp,W1,W2,g):
    hidden=[max(0,a) for a in fp.mv(W1,fp.norm(g))]
    out=addvec(fp,g,fp.mv(W2,hidden))
    assert sum(x>0 for x in hidden)==1 and max(hidden)==D,hidden
    return out,hidden

def materialized(fp,state,k,v):
    n=len(k)
    # All omitted rows and columns are structurally zero: K and V vanish there
    # and the state begins zero. Active I-kk^T is materialized before use.
    A=[[fp.add(D if i==j else 0,-fp.mul(k[i],k[j])) for j in range(n)] for i in range(n)]
    return [[fp.add(fp.dot(nz(A[i]),[state[t][j] for t in range(n)]),fp.mul(k[i],v[j])) for j in range(len(v))] for i in range(n)]

class MarkerLayer:
    def __init__(self,fp):
        self.fp=fp;self.state=[[0]*2 for _ in range(4)]
        fixed=[-5*D//6,-3*D//6,-D//6,-D//6]
        self.K=fp.params([[(26,2*x)] for x in fixed]);self.Q=fp.params([[(26,2*D)],[],[],[]])
        self.V=fp.params([[(26,4)],[(26,2)]])
        O=[[] for _ in range(WIDTH)]
        O[14]=[(0,D*D//2),(1,-3*D*D//2)];O[15]=[(i,-w) for i,w in O[14]]
        O[12]=[(0,-D*D//2),(1,D*D)];O[13]=[(i,-w) for i,w in O[12]]
        O[26]=[(1,D*D//2)];O[27]=[(1,-D*D//2)];self.O=fp.params(O)
        W1=[];W2=[[] for _ in range(WIDTH)]
        for a in range(3):
            for B in range(2):
                row=[-2*D if i in (0,2,4) else 0 for i in range(WIDTH)]
                row[2*a]+=2*D;row[12+2*B]=2*D;W1.append(nz(row))
                g=[0]*WIDTH;g[2*a:2*a+2]=[D//2,-D//2];g[12+2*B:14+2*B]=[D//2,-D//2]
                delta=difference(canonical(2*a+B),g)
                for i,x in enumerate(delta):
                    if x:W2[i].append((2*a+B,x))
        self.W1=fp.params(W1+[[] for _ in range(12)]);self.W2=fp.params(W2)
    def step(self,h):
        fp=self.fp;h0=fp.norm(h);x=fp.norm(h0)
        k=fp.mv(self.K,x);q=fp.mv(self.Q,x);v=fp.mv(self.V,x)
        self.state=materialized(fp,self.state,k,v)
        out=[fp.dot(nz(q),[self.state[i][j] for i in range(4)]) for j in range(2)]
        y=fp.norm(fp.mv(self.O,out));g=addvec(fp,h0,y)
        result,hidden=ff(fp,self.W1,self.W2,g)
        fp.norm(result)
        return result,dict(state=[r[:] for r in self.state],read=out,write=y,hidden=hidden)

class CyclicLayer:
    def __init__(self,fp):
        self.fp=fp;self.state=[[0]*5 for _ in range(9)]
        self.K=fp.params([[(26,2*D//3)] for _ in range(9)])
        self.Q=fp.params([[(26,2*D)]]+[[] for _ in range(8)])
        values=[]
        for a,B in ((a,B) for a in range(3) for B in range(2)):
            values.append([(a+c*B)*D//L for c in PHASES[0]]+[3*a*D//L,3*D//L])
        self.V=linear(fp,6,values,5)
        O=[[] for _ in range(WIDTH)]
        for j in range(3):
            O[12+2*j]=[(j,3*L*D//4),(3,-L*D//4)]
            O[13+2*j]=[(i,-w) for i,w in O[12+2*j]]
        for i in (18,20):O[i]=[(4,L*D//4)];O[i+1]=[(4,-L*D//4)]
        O[26]=[(4,-L*D//2)];O[27]=[(4,L*D//2)];self.O=fp.params(O)
        W1=[];W2=[[] for _ in range(WIDTH)]
        for s in range(3):
            for label in range(6):
                a,B=divmod(label,2);row=[0]*WIDTH
                for j,c in enumerate(PHASES[s]):row[12+2*j]=4*c*D
                row[2*label]=2*D;row[18]=-8*D;W1.append(nz(row))
                g=[0]*WIDTH;g[2*label:2*label+2]=[D//2,-D//2]
                for j,c in enumerate(PHASES[s]):g[12+2*j:14+2*j]=[c*D//4,-c*D//4]
                for i in (18,20):g[i:i+2]=[D//4,-D//4]
                delta=difference(canonical((s+a)%3),g)
                for i,x in enumerate(delta):
                    if x:W2[i].append((6*s+label,x))
        self.W1=fp.params(W1);self.W2=fp.params(W2)
        self.U=fp.params([[(2*a,2*D)] for a in range(3)])
    def step(self,h):
        fp=self.fp;h0=fp.norm(h);x=fp.norm(h0)
        k=fp.mv(self.K,x);q=fp.mv(self.Q,x);v=fp.mv(self.V,x)
        self.state=materialized(fp,self.state,k,v)
        out=[fp.dot(nz(q),[self.state[i][j] for i in range(9)]) for j in range(5)]
        y=fp.norm(fp.mv(self.O,out));g=addvec(fp,h0,y)
        result,hidden=ff(fp,self.W1,self.W2,g)
        scores=fp.mv(self.U,fp.norm(result));decoded=max(range(3),key=lambda a:scores[a])
        assert scores==[D*int(a==decoded) for a in range(3)],scores
        return result,dict(state=[r[:] for r in self.state],read=out,write=y,hidden=hidden,scores=scores,decoded=decoded)

class Module:
    def __init__(self,fp):self.marker=MarkerLayer(fp);self.cyclic=CyclicLayer(fp)
    def step(self,h):
        h,m=self.marker.step(h);h,c=self.cyclic.step(h);return h,dict(marker=m,cyclic=c)

def main():
    fp=Fixed();marker=MarkerLayer(fp);cyclic=CyclicLayer(fp)
    zero=[[0]*2 for _ in range(4)]
    u=[[-2,-1],[-1,0],[0,0],[0,0]];stable=[[-3,-1],[-1,0],[0,0],[0,0]]
    marker_cases=[]
    for stage,state in enumerate((zero,u,stable)):
        for a in range(3):
            marker.state=[r[:] for r in state];out,trace=marker.step(canonical(a))
            expected=u if stage==0 else stable
            assert marker.state==expected,(stage,a,marker.state)
            B=int(stage==0);assert out==canonical(2*a+B)
            marker_cases.append(dict(stage=stage,input=a,first=B,trace=trace))
    cyclic_cases=[]
    cases=[('initial',0,0,None)]+[('raw',a,s,[3*(a+c) for c in PHASES[s]]+[9*a,9]) for a,s in __import__('itertools').product(range(3),range(3))]
    for name,previous_a,exclusive,raw in cases:
        for a in range(3):
            cyclic.state=[[0]*5 for _ in range(9)] if raw is None else [raw[:] for _ in range(9)]
            B=int(raw is None);h,trace=cyclic.step(canonical(2*a+B))
            s=0 if raw is None else (exclusive+previous_a)%3
            expected=[3*(a+c) for c in PHASES[s]]+[9*a,9]
            assert cyclic.state==[expected]*9,(name,previous_a,exclusive,a,cyclic.state,expected)
            assert h==canonical((s+a)%3)
            cyclic_cases.append(dict(kind=name,previous_input=previous_a,previous_phase=exclusive,input=a,first=B,trace=trace))
    modules=[Module(fp),Module(fp)];word=[0,1,2,1,1,0,2,2,1,0,2];prefix=0;double=0;stream=[]
    for a in word:
        h,first=modules[0].step(canonical(a));h,second=modules[1].step(h)
        prefix=(prefix+a)%3;double=(double+prefix)%3
        assert first['cyclic']['decoded']==prefix and second['cyclic']['decoded']==double
        assert h==canonical(double)
        stream.append(dict(input=a,prefix=prefix,prefix_of_prefix=double,first=first,second=second))
    return fp,dict(marker_cases=marker_cases,cyclic_cases=cyclic_cases,stream=stream)

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_CPU,(30,30));signal.alarm(45)
    start=time.perf_counter();cpu=time.process_time();fp=None
    result=dict(status='FAIL',scope='independent unit Euclidean constant-norm two-layer Z3 module reproduction; finite local transitions and stacked stream, not published theorem',D=D,L=L,p=P,width=WIDTH,heads_per_layer=1,layers_per_module=2,ff_width=18,rounding='nearest ties upward, individual products and left-to-right sums; absorbing pre-round overflow',mean_implementations='sum/n and sum individually rounded coordinate*(1/n), checked equal on every call',supplier_artifacts_read=False)
    try:fp,data=main();result.update(data);result['status']='PASS'
    except Exception as exc:result.update(earliest_obligation=str(exc),traceback=traceback.format_exc())
    if fp is not None:result.update(max_parameter_numerator=fp.max_parameter,max_pre_round_numerator=str(fp.max_intermediate),max_operation=fp.max_operation,scalar_operations=fp.operations,normalization_calls=fp.norm_calls,absorbing_overflow=fp.overflow)
    result.update(wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    path=Path(__file__).parent/'evidence'/'independent-constant-result.json';path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['marker_cases','cyclic_cases','stream','traceback']},sort_keys=True))
    if result['status']!='PASS':print(result['traceback']);raise SystemExit(1)
