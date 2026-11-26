"""Residuals and feasible numerical references, NOT a global-optimality certificate."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shared54 import *
from scipy.optimize import minimize
A=np.log(2)**2


def simplex_grid(k,total,prefix=()):
    if k==1:
        yield prefix+(total,);return
    for i in range(total+1):yield from simplex_grid(k-1,total-i,prefix+(i,))


def direct_mass(e,seg,lam,w,G,H,S,K):
    a=-np.expm1(-lam*H);rest=np.maximum(0,lam*H-a)
    def occupancy(T):return float(np.dot(w*(-np.expm1(-lam*min(T,H))),e[seg])+np.dot(G,e)*min(T,H)/H)
    if S==0:T=0.;saturated=False
    elif occupancy(1000*H)<=S:T=1000*H;saturated=True
    else:
        lo=0.;hi=H
        for _ in range(70):
            mid=(lo+hi)/2
            if occupancy(mid)>S:hi=mid
            else:lo=mid
        T=(lo+hi)/2;saturated=False
    mass=np.bincount(seg,weights=w*(a+rest*np.exp(-lam*T)),minlength=K)+G
    return mass,T,saturated,occupancy(T)


def reference(n,bits,objective,baseline,hstart):
    active=n>0;k=int(active.sum());budget=max(float(bits),0.);rng=np.random.default_rng(5401)
    def eps(shares):
        e=np.zeros(len(n));e[active]=np.exp(-np.minimum(700.,A*budget*np.maximum(shares,0)/n[active]));return e
    def shares(e):
        x=n[active]*(-np.log(np.clip(e[active],1e-300,1)))/A
        return x/x.sum() if x.sum() else np.full(k,1/k)
    t=time.perf_counter();gridbest=None;gridcount=0
    for point in simplex_grid(k,12):
        x=np.array(point,float)/12;value=objective(eps(x));gridcount+=1
        if gridbest is None or value<gridbest[0]:gridbest=value,x
    starts=[np.full(k,1/k),shares(hstart),shares(baseline),gridbest[1],*rng.dirichlet(np.ones(k),size=3)]
    norm=max(objective(baseline),1.);out=[];feasible=[(objective(baseline),baseline,'original3'),(gridbest[0],eps(gridbest[1]),'coarse-grid')]
    for i,x in enumerate(starts):
        opt=minimize(lambda v:objective(eps(v))/norm,x,method='SLSQP',bounds=[(0,1)]*k,constraints=[{'type':'eq','fun':lambda v:v.sum()-1}],options=dict(ftol=1e-10,maxiter=300))
        ok=bool(np.isfinite(opt.x).all() and opt.x.min()>=-1e-8 and abs(opt.x.sum()-1)<1e-7)
        value=None
        if ok:
            xx=np.maximum(opt.x,0);xx/=xx.sum();e=eps(xx);used=float(np.dot(n[active],-np.log(e[active]))/A)
            assert used<=budget+max(1e-6,budget*1e-8);value=objective(e);feasible.append((value,e,f'SLSQP{i}'))
        out.append(dict(start=i,success=bool(opt.success),feasible=ok,message=str(opt.message),iterations=int(opt.nit),objective=value))
    best=min(feasible,key=lambda x:x[0]);f3=objective(baseline)
    return dict(objective3=f3,best_observed_feasible=best[0],best_source=best[2],epsilon_best=best[1].tolist(),gap3_over_best=(f3-best[0])/best[0] if best[0]>0 else None,coarse_grid_points=gridcount,coarse_grid_best=gridbest[0],local_runs=out,wall_s=time.perf_counter()-t,global_optimum_certified=False)


def analyze(d,kib,gama):
    start=time.perf_counter()
    with scope(d.cache):anchor=E5.build(d.s,d.scores,gama['trees'],kib,.1)
    td=E5.tree(d.s,d.scores,anchor['trees']);reg=E5.D.region_of_segment(anchor['structure'].b);nr=len(anchor['structure'].f)
    n=np.bincount(reg,weights=td.g,minlength=nr);h=np.bincount(reg,weights=td.h,minlength=nr)
    lr=d.lm;region=reg[td.seg_q[lr.keys]];rates,ridx=np.unique(lr.rate,return_inverse=True);counts=np.bincount(region*len(rates)+ridx,minlength=nr*len(rates));nz=np.flatnonzero(counts)
    seg=nz//len(rates);lam=rates[nz%len(rates)];w=counts[nz].astype(float);H=len(d.tail);G=H*lr.N1/lr.L*h
    P=RA.ra4.Population(seg,lam,w,G,n,h,H);S=anchor['slots'];bits=(kib*1024-td.fixed-anchor['cache_bytes'])*8
    values={i:RA.ra4.solve(P,S,bits,'ra',refine=i,setassoc=True)[0] for i in range(22)};hist=[]
    for i in (0,1,2,3,5,10,20):
        e=values[i];nxt=values[i+1];f=float(e@P.misses(e,S,True));fn=float(nxt@P.misses(nxt,S,True))
        mass,T,sat,occ=direct_mass(e,seg,lam,w,G,H,S,nr);mn,Tn,sn,on=direct_mass(nxt,seg,lam,w,G,H,S,nr)
        eps_res=float(np.max(np.abs(nxt-e)));obj_res=abs(fn-f)/max(abs(f),1e-300)
        hist.append(dict(iteration=i,epsilon=e.tolist(),objective_SA=f,epsilon_next_residual_inf=eps_res,objective_next_relative_change=obj_res,passes_both_residual_thresholds=eps_res<=1e-6 and obj_res<=1e-6,effective_FA_T=T,T_next_relative_change=abs(Tn-T)/max(1.,T),FA_saturated=sat,effective_FA_occupancy=occ,possible_two_cycle=bool(i>=2 and np.max(np.abs(e-values[i-2]))<1e-6 and np.max(np.abs(e-values[i-1]))>1e-6)))
    fsa=lambda e:float(e@P.misses(e,S,True))
    ffa=lambda e:float(e@direct_mass(e,seg,lam,w,G,H,S,nr)[0])
    eps3=values[3];hstart=RA.ra4.eps_closed(h,n,bits)
    return dict(trees=anchor['trees'],cache_slots=S,cache_bytes=anchor['cache_bytes'],partition=anchor['structure'].b.tolist(),n=n.tolist(),h=h.tolist(),bits=int(bits),iterations=hist,numerical_SA_grid_objective=reference(n,bits,fsa,eps3,hstart),numerical_FA_direct_objective=reference(n,bits,ffa,eps3,hstart),T_scope='T is equivalent fully-associative diagnostic; Poisson-SA has a capacity mixture, not a single physical T',fixed_partition_only=True,actual_CLOCK_optimality_claim=False,wall_s=time.perf_counter()-start)
