"""First-party unit-norm Z3 wreath U2 compiler, reconstructed from equations.

Sparse matrices omit structurally zero products only;
ordered nonzero products retain increasing input-coordinate order. Every cache
miss executes the fixed-point projections, materialized recurrence, O, actual
normalizations, residual and FF. Reference monoid operations occur only in
construction and in the separate exhaustive verifier, never in Network.step.
"""
from itertools import product
from math import isqrt
from pathlib import Path
import hashlib,json,resource,signal,time,traceback

D=96768; M=672; HD=336; P=64; LIMIT=2**P
SH=670; WORK=648; FF_WIDTH=972
TOKENS=tuple(product(range(3),repeat=4)) # f0,f1,f2,n
C3=((0,1,-1),(1,-1,0),(-1,0,1))
C2=((0,1),(1,0))

class FP:
    def __init__(self):
        self.operations=0;self.norm_calls=0;self.max_parameter=0
        self.max_pre_n=0;self.max_pre_d=1;self.overflow=False
    def check(self,n,d=1):
        if self.overflow or abs(n)>LIMIT*d:
            self.overflow=True;raise OverflowError(('absorbing pre-round overflow',n,d))
        if abs(n)*self.max_pre_d>self.max_pre_n*d:self.max_pre_n,self.max_pre_d=abs(n),d
        return n
    def add(self,a,b):self.operations+=1;return self.check(a+b)
    def rnd(self,n,d):
        self.check(n,d);self.operations+=1;return self.check((2*n+d)//(2*d))
    def mul(self,a,b):return self.rnd(a*b,D)
    def dot(self,row,x):
        s=0
        for i,w in row:
            if x[i]:s=self.add(s,self.mul(w,x[i]))
        return s
    def norm(self,v):
        assert len(v)==M
        nz=[x for x in v if x]
        total=0;other=0
        for x in nz:
            total=self.add(total,x);other=self.add(other,self.mul(x,D//M))
        mean=self.rnd(total,M)
        assert mean==other==0,('nonzero mean',mean,other)
        ss=0
        for x in nz:ss=self.add(ss,self.mul(x,x))
        assert ss==D,('nonunit squared norm',ss,[(i,x) for i,x in enumerate(v) if x])
        root=isqrt(ss*D)
        if 4*ss*D>=(2*root+1)**2:root+=1
        self.check(root);assert root==D
        out=[self.rnd(x*D,root) if x else 0 for x in v]
        assert out==v;self.norm_calls+=1;return out

class Mat:
    def __init__(self,fp,rows,nin):
        self.rows=tuple(tuple(sorted((i,w) for i,w in row if w)) for row in rows)
        self.cols={};self.nout=len(rows);self.nin=nin
        for j,row in enumerate(self.rows):
            assert len({i for i,w in row})==len(row)
            for i,w in row:
                assert 0<=i<nin;fp.check(w);fp.max_parameter=max(fp.max_parameter,abs(w))
                self.cols.setdefault(i,[]).append((j,w))
    def __call__(self,fp,x):
        assert len(x)==self.nin
        out=[0]*self.nout
        for i,a in enumerate(x):
            if a:
                for j,w in self.cols.get(i,()):out[j]=fp.add(out[j],fp.mul(w,a))
        return out

def canonical(z):
    assert 0<=z<324
    v=[0]*M;v[2*z:2*z+2]=[D//2,-D//2];v[SH:SH+2]=[D//2,-D//2];return v
def add(fp,a,b):return [fp.add(x,y) if x or y else 0 for x,y in zip(a,b)]
def difference(a,b):return [x-y for x,y in zip(a,b)]
def paired(v,start,values):
    for j,a in enumerate(values):v[start+2*j:start+2*j+2]=[a,-a]
def projection(fp,labels,targets):
    n=len(targets[0]);return Mat(fp,[[(2*z,2*targets[z][j]) for z in range(len(labels)) if targets[z][j]] for j in range(n)],M)

class Head:
    """Only active rows/columns stored. All omitted rows have K=Q=V=S0=0."""
    def __init__(self,fp,K,Q,V,B=None):
        self.K=K;self.Q=Q;self.V=V;self.B=B;self.rows=K.nout;self.cols=V.nout
        assert self.rows<=HD and self.cols<=HD
        self.zero=tuple(tuple(0 for _ in range(self.cols)) for _ in range(self.rows))
        self.cache={};self.fp=fp
    def step(self,state,x):
        fp=self.fp;k=self.K(fp,x);q=self.Q(fp,x);v=self.V(fp,x)
        beta=D if self.B is None else self.B(fp,x)[0]
        assert beta in (0,D)
        sq=0
        for a in k:sq=fp.add(sq,fp.mul(a,a))
        assert sq==D,('nonunit key norm',sq)
        A=[[fp.add(D if i==j else 0,-fp.mul(beta,fp.mul(k[i],k[j]))) for j in range(self.rows)] for i in range(self.rows)]
        out=[]
        for i in range(self.rows):
            row=[]
            for j in range(self.cols):
                z=0
                for t in range(self.rows):z=fp.add(z,fp.mul(A[i][t],state[t][j]))
                row.append(fp.add(z,fp.mul(beta,fp.mul(k[i],v[j]))))
            out.append(tuple(row))
        state=tuple(out);read=[]
        for j in range(self.cols):
            z=0
            for i in range(self.rows):z=fp.add(z,fp.mul(q[i],state[i][j]))
            read.append(z)
        return state,read

def constant_rows(fp,vals):return Mat(fp,[[(SH,2*v)] if v else [] for v in vals],M)
def overwrite_head(fp,labels,values,key_targets=None,query_targets=None):
    K=constant_rows(fp,[D]) if key_targets is None else projection(fp,labels,key_targets)
    Q=constant_rows(fp,[D]) if query_targets is None else projection(fp,labels,query_targets)
    return Head(fp,K,Q,projection(fp,labels,values))
def dummy(fp):return Head(fp,constant_rows(fp,[D]),constant_rows(fp,[0]),constant_rows(fp,[0]))

class FF:
    def __init__(self,fp,rows,deltas):
        assert len(rows)<=FF_WIDTH
        self.W1=Mat(fp,rows+[[] for _ in range(FF_WIDTH-len(rows))],M)
        self.W2=Mat(fp,[[(j,delta[i]) for j,delta in enumerate(deltas) if delta[i]] for i in range(M)],FF_WIDTH)
    def step(self,fp,g):
        h=[max(0,x) for x in self.W1(fp,fp.norm(g))]
        active=[i for i,x in enumerate(h) if x]
        assert len(active)==1 and h[active[0]]==D,('FF not exact onehot',active,[h[i] for i in active])
        out=add(fp,g,self.W2(fp,h));fp.norm(out)
        return out

class Layer:
    def __init__(self,fp,labels,heads,O,ff,outlabels):
        self.fp=fp;self.labels=tuple(labels);self.heads=heads;self.O=O;self.ff=ff;self.outlabels=tuple(outlabels)
        self.zero=tuple(h.zero for h in heads);self.cache={};self.outputs={tuple(canonical(i)):i for i in range(len(outlabels))}
    def step(self,state,label):
        key=(state,label)
        if key in self.cache:return self.cache[key]
        fp=self.fp;h0=fp.norm(canonical(label));x=fp.norm(h0)
        states=[];reads=[]
        for head,old in zip(self.heads,state):
            new,read=head.step(old,x);states.append(new);reads+=read+[0]*(HD-len(read))
        y=fp.norm(self.O(fp,reads));g=add(fp,h0,y);out=self.ff.step(fp,g)
        result=(tuple(states),self.outputs[tuple(out)])
        self.cache[key]=result;return result

def build_joint(fp,labels,cases,carrier_values,target):
    """Paired onehot carrier with cancelled shared pair; exact conjunction FF."""
    rows=[];deltas=[]
    for label in range(len(labels)):
        for c in range(cases):
            row={2*j:-2*D for j in range(len(labels))};row[2*label]+=2*D;row[WORK+2*c]=2*D
            rows.append(list(row.items()))
            g=[0]*M;paired(g,2*label,[D//2]);paired(g,WORK,carrier_values(c))
            deltas.append(difference(canonical(target(label,c)),g))
    return FF(fp,rows,deltas)

def marker(fp):
    labels=TOKENS;outlabels=tuple((t,B) for t in labels for B in range(2))
    k=[-5*D//6,-3*D//6,-D//6,-D//6]
    h=Head(fp,constant_rows(fp,k),constant_rows(fp,[D,0,0,0]),constant_rows(fp,[2,1]))
    O=[[] for _ in range(M)]
    # B=D*sigma-3D*gamma; C=-D*gamma=1, order (B0,B1).
    O[WORK]=[(0,-D*D//2),(1,D*D)];O[WORK+1]=[(i,-w) for i,w in O[WORK]]
    O[WORK+2]=[(0,D*D//2),(1,-3*D*D//2)];O[WORK+3]=[(i,-w) for i,w in O[WORK+2]]
    O[SH]=[(1,D*D//2)];O[SH+1]=[(1,-D*D//2)]
    ff=build_joint(fp,labels,2,lambda c:[D//2*int(j==c) for j in range(2)],lambda l,c:2*l+c)
    return Layer(fp,labels,[h,dummy(fp)],Mat(fp,O,2*HD),ff,outlabels)

def cyclic(fp,labels,m,increment,target,outlabels):
    H=m-1;C=C2 if m==2 else C3;L=D//(m*m);n=m*m
    # Every phase row is materialized, including diagonal/off-diagonal rounding.
    vals=[]
    for label in labels:
        a,B=increment(label)
        vals.append([(a+C[0][j]*B)*D//L for j in range(m)]+[(H+1)*a*D//L,(H+1)*D//L])
    head=Head(fp,constant_rows(fp,[D//m]*n),constant_rows(fp,[D]+[0]*(n-1)),projection(fp,labels,vals))
    O=[[] for _ in range(M)]
    for j in range(m):
        # q=e1 reads m(a+u), whereas overwrite columns read m²a,m².
        # Therefore phase projection includes the necessary extra factor m.
        O[WORK+2*j]=[(j,m*L*D//(H+1)),(m,-L*D//(H+1))]
        O[WORK+2*j+1]=[(i,-w) for i,w in O[WORK+2*j]]
    O[WORK+2*m]=[(m+1,L*(H-1)*D//(2*(H+1)))];O[WORK+2*m+1]=[(i,-w) for i,w in O[WORK+2*m]]
    O[SH]=[(m+1,-L*D//2)];O[SH+1]=[(m+1,L*D//2)]
    rows=[];deltas=[]
    for label in range(len(labels)):
        for s in range(m):
            row={2*j:-2*H*D for j in range(len(labels))};row[2*label]+=2*D
            for j,c in enumerate(C[s]):row[WORK+2*j]=(H+1)*c*D
            rows.append(list(row.items()))
            g=[0]*M;paired(g,2*label,[D//2]);paired(g,WORK,[c*D//(H+1) for c in C[s]]+[(H-1)*D//(2*(H+1))])
            deltas.append(difference(canonical(target(label,s)),g))
    return Layer(fp,labels,[head,dummy(fp)],Mat(fp,O,2*HD),FF(fp,rows,deltas),outlabels)

def prefix(fp,labels):
    outlabels=tuple((f,B,p,n) for f in product(range(3),repeat=3) for B in range(2) for p in range(2) for n in range(3))
    index={t:i for i,t in enumerate(outlabels)}
    # Constant alpha=beta=1. Identity writes only inert row 0; row 1
    # retains the previous reset state. Reset tokens overwrite row 1.
    keys=[[D*int(t[0][3]==0),D*int(t[0][3]!=0)] for t in labels]
    queries=[[0,D] for _ in labels]
    values=[[D*int(t[0][3]==n) for n in (1,2)] for t in labels]
    main=Head(fp,projection(fp,labels,keys),projection(fp,labels,queries),projection(fp,labels,values))
    assert main.B is None
    comp=overwrite_head(fp,labels,[[D] for _ in labels])
    O=[[] for _ in range(M)]
    O[WORK]=[(0,-D//2),(1,-D//2),(HD,D//2)]
    O[WORK+2]=[(0,D//2)];O[WORK+4]=[(1,D//2)]
    for j in range(3):O[WORK+2*j+1]=[(i,-w) for i,w in O[WORK+2*j]]
    O[SH]=[(HD,-D//2)];O[SH+1]=[(HD,D//2)]
    ff=build_joint(fp,labels,3,lambda c:[D//2*int(j==c) for j in range(3)],lambda l,n:index[(labels[l][0][:3],labels[l][1],labels[l][2],n)])
    return Layer(fp,labels,[main,comp],Mat(fp,O,2*HD),ff,outlabels)

def delay(fp,labels):
    outlabels=tuple((n,u,B) for n in range(3) for u in product(range(3),repeat=3) for B in range(2));index={t:i for i,t in enumerate(outlabels)}
    kval=[[D*int(p==j) for j in range(2)] for f,B,p,n in labels]
    qval=[[D*int(1-p==j) for j in range(2)] for f,B,p,n in labels]
    values=[[D*int(n==j) for j in range(3)] for f,B,p,n in labels]
    main=overwrite_head(fp,labels,values,kval,qval)
    comp=overwrite_head(fp,labels,[[B*D,D] for f,B,p,n in labels])
    O=[[] for _ in range(M)]
    for j in range(3):
        O[WORK+2*j]=[(j,D//2)]+([(HD,D//2)] if j==0 else [])
        O[WORK+2*j+1]=[(i,-w) for i,w in O[WORK+2*j]]
    O[SH]=[(HD+1,-D//2)];O[SH+1]=[(HD+1,D//2)]
    def target(l,prev):
        f,B,p,n=labels[l];u=tuple(f[x if prev==0 else prev] for x in range(3))
        return index[n,u,B]
    ff=build_joint(fp,labels,3,lambda c:[D//2*int(j==c) for j in range(3)],target)
    return Layer(fp,labels,[main,comp],Mat(fp,O,2*HD),ff,outlabels)

class Network:
    def __init__(self,fp):
        self.fp=fp;self.layers=[marker(fp)]
        labels=self.layers[-1].outlabels
        outlabels=tuple((t,B,p) for t,B in labels for p in range(2));index={t:i for i,t in enumerate(outlabels)}
        self.layers.append(cyclic(fp,labels,2,lambda t:(1,t[1]),lambda l,s:index[(*labels[l],(s+1)%2)],outlabels))
        self.layers.append(prefix(fp,outlabels));self.layers.append(delay(fp,self.layers[-1].outlabels))
        for j in range(3):
            labels=self.layers[-1].outlabels;index={t:i for i,t in enumerate(labels)}
            def target(l,s,j=j,labels=labels,index=index):
                n,u,B=labels[l];v=list(u);v[j]=(v[j]+s)%3;return index[n,tuple(v),B]
            self.layers.append(cyclic(fp,labels,3,lambda t,j=j:(t[1][j],t[2]),target,labels))
        self.zero=tuple(l.zero for l in self.layers)
        labels=self.layers[-1].outlabels
        self.U=Mat(fp,[[(2*l,2*D) for l,(n,u,B) in enumerate(labels) if (*u,n)==t] for t in TOKENS],M)
        self.readouts={}
    def step(self,state,token):
        states=[];label=token
        for layer,old in zip(self.layers,state):
            new,label=layer.step(old,label);states.append(new)
        if label not in self.readouts:
            scores=self.U(self.fp,self.fp.norm(canonical(label)))
            z=max(range(81),key=lambda j:scores[j]);assert scores==[D*int(j==z) for j in range(81)]
            self.readouts[label]=z
        return tuple(states),self.readouts[label]

def reference(prev,t):
    f=t[:3];n=t[3];F,N=prev
    return tuple((F[x]+f[x if N==0 else N])%3 for x in range(3)),N if n==0 else n

def exhaustive(net):
    """Full physical-state BFS; reference is never a model argument."""
    states=[net.zero];refs=[((0,0,0),0)];seen={net.zero:0};edges=0;depth=[0];hist={0:1}
    pos=0
    while pos<len(states):
        old=states[pos];ref=refs[pos]
        for t,token in enumerate(TOKENS):
            new,out=net.step(old,t);expected=reference(ref,token);edges+=1
            assert TOKENS[out]==(*expected[0],expected[1]),('wrong monoid output',pos,t,TOKENS[out],expected)
            if new in seen:assert refs[seen[new]]==expected,('physical state alias',pos,t)
            else:
                seen[new]=len(states);states.append(new);refs.append(expected);d=depth[pos]+1;depth.append(d);hist[d]=hist.get(d,0)+1
        pos+=1
        if pos%250==0:print(json.dumps(dict(progress_states=pos,discovered=len(states),edges=edges)),flush=True)
    witnesses=[]
    g=(0,0,1)
    for reset in (1,2):
        state=net.zero;word=[(0,0,0,reset),(*g,1)];outputs=[]
        for tok in word:state,out=net.step(state,TOKENS.index(tok));outputs.append(TOKENS[out])
        assert outputs[-1][0]==reset-1
        witnesses.append(dict(word=word,outputs=outputs))
    # The first identity token and its actual initialized/reset-buffer behavior.
    st,out=net.step(net.zero,TOKENS.index((0,0,0,0)));assert TOKENS[out]==(0,0,0,0)
    return dict(states=len(states),edges=edges,frontier_exhausted=pos==len(states),depth_histogram=hist,reset_witnesses=witnesses,first_identity_output=TOKENS[out])

def main():
    start=time.perf_counter();cpu=time.process_time();fp=FP();net=None
    result=dict(status='FAIL',scope='complete 81-input/81-output reachable transition certificate for unit Euclidean norm and literal unit keys',D=D,p=P,width=M,heads_per_layer=2,head_width=HD,layers=7,ff_width=FF_WIDTH,input_alphabet=81,output_alphabet=81,literal_unit_keys=True,first_flag_source='actual marker head state',parity_source='actual C2 phase head state',supplier_artifacts_read=False,reference_feeds_model=False,zero_omission='only exact zero products/additions, input coordinate order retained',resource_limits=dict(cpu_seconds=60,wall_seconds=90,threads=1,rss_gib=1))
    try:
        net=Network(fp);result['compile_seconds']=time.perf_counter()-start
        # Bounded single-unit smoke, including both reset witnesses, before BFS.
        for word in (((0,0,0,0),),((0,0,0,1),(0,0,1,1)),((0,0,0,2),(0,0,1,1))):
            state=net.zero;ref=((0,0,0),0)
            for token in word:
                state,out=net.step(state,TOKENS.index(token));ref=reference(ref,token)
                assert TOKENS[out]==(*ref[0],ref[1]),('unit smoke mismatch',word,token,TOKENS[out],ref)
        result['unit_smoke']='PASS';result.update(exhaustive(net));result['status']='PASS'
    except BaseException as exc:result.update(earliest_obligation=str(exc),traceback=traceback.format_exc())
    result.update(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scalar_operations=fp.operations,norm_calls=fp.norm_calls,max_parameter_numerator=fp.max_parameter,max_pre_round_numerator=f'{fp.max_pre_n}/{fp.max_pre_d}',absorbing_overflow=fp.overflow)
    if net is not None:result.update(local_cache_entries=[len(l.cache) for l in net.layers],readout_cache_entries=len(net.readouts))
    result['source_hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),Path(__file__).with_name('independent_constant_norm.py'),Path(__file__).with_name('independent_wreath.py'))}
    path=Path(__file__).parent/'evidence'/'independent-wreath-unit-keys-result.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='traceback'},sort_keys=True),flush=True)
    if result['status']!='PASS':print(result.get('traceback',''));return 1
    return 0

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    def timeout(signum,frame):raise TimeoutError('90-second wall budget reached')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(90)
    raise SystemExit(main())
