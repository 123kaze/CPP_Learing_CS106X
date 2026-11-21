import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mechanism28 import *
import hashlib
import json
import time
import ctypes
from numba import get_num_threads

SETTINGS={'url':(16,128),'caida_tcp_flow':(1,32)}
AMPLITUDES=(-1.5,-1.,-.5,0.,.5,1.,1.5)
BPMS=(2,8)
TTLS=(1000,10000)
SEEDS=(2801,2802,2803)
H=300000


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ah(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(path)


def check():
    manifest=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,h in manifest['sources'].items():assert sha(BLOOM/rel)==h,rel
    return sha(ROOT/'plan/freeze.json')


def run(ds,path):
    frozen=check();start=time.perf_counter()
    lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));f=lib.openblas_get_num_threads;f.restype=ctypes.c_int
    assert f()==get_num_threads()==1
    if ds.endswith('_tcp_flow'):
        sys.path.insert(0,str(WR/'round11_tcp/src'));import tcp11
    timer=time.perf_counter();s,scores,_=E5.load(ds);t,kib=SETTINGS[ds]
    base=E5.build(s,scores,t,kib,0.);td=E5.tree(s,scores,t);reg=E5.D.region_of_segment(base['structure'].b)
    rm=reg[td.seg_m].astype(np.int32);rq=base['structure'].q_region.astype(np.int32);n=np.bincount(rm,minlength=5)
    h=np.bincount(reg,weights=td.h,minlength=5);prep_s=time.perf_counter()-timer
    assert np.isclose(h.sum(),1.)
    # Freeze imports lazily loaded by legacy setup too (listed proactively by run28.freeze).
    check()
    metadata=dict(status='running',dataset=ds,freeze_sha256=frozen,tree_count=t,partition_source_budget_kib=kib,partition_bounds=base['structure'].b.tolist(),
                  members=n.tolist(),validation_mass=h.tolist(),negative_region_counts=np.bincount(rq,minlength=5).tolist(),horizon=H,prep_seconds=prep_s,
                  model_payload_bytes=td.model_bytes,model_metadata_headers_fixed_bytes=td.fixed,backend_index_payload_bytes=len(s.h1m)*8,
                  input_hashes={name:sha(E5.C.CACHE/ds/name) for name in ('data.npz','gama_scores.npz','model200.txt')},cases=[])
    for amp in AMPLITUDES:
        prob,region_mass,exponents=probabilities(rq,h,amp)
        cdf=np.cumsum(prob);cdf[-1]=1.
        for seed in SEEDS:
            rng=np.random.default_rng(seed);timer=time.perf_counter();stream=np.searchsorted(cdf,rng.random(H)).astype(np.int64);stream_s=time.perf_counter()-timer
            # An additional bijective hash mix changes BF/hash seed, not key identity/region.
            mh=E5.C.splitmix64(s.h1m^np.uint64(seed));qh=E5.C.splitmix64(s.h1q^np.uint64(seed))
            timer=time.perf_counter();safe=E5.E.CC.safe_prefix_lengths(np.sort(mh),qh);safe_s=time.perf_counter()-timer
            for T in TTLS:
                timer=time.perf_counter();Mc,Me,chekey,exactkey=masses(prob,rq,T,H,len(n));M_s=time.perf_counter()-timer
                timer=time.perf_counter();miss=ttl_misses(stream,len(qh),T);ttl_prepare_s=time.perf_counter()-timer
                for bpm in BPMS:
                    bits=int(n.sum()*bpm)//8*8
                    pc=identity(n,h,Mc,bits);pe=identity(n,h,Me,bits)
                    configs={'h':pc['baseline_epsilon'],'paper_M':pc['reweighted_epsilon'],'exact_M':pe['reweighted_epsilon']};arms={}
                    for name,eps in configs.items():
                        timer=time.perf_counter();flags,mem=physical(n,np.array(eps),mh,qh,rm,rq,bits);build_s=time.perf_counter()-timer
                        timer=time.perf_counter();ttl_fp=int(miss[flags].sum());ttl_sum_s=time.perf_counter()-timer
                        timer=time.perf_counter();cl,cb=clock(stream,qh,safe,flags,mh);clock_s=time.perf_counter()-timer
                        arms[name]=dict(**mem,static_fp_keys=int(flags.sum()),static_flags_sha256=ah(flags),ttl_fp=ttl_fp,clock=cl,cache_physical_bytes=cb,
                                        ttl_expected_fp_given_static_bf=float(exactkey[flags].sum()),paper_predicted_fp_given_static_bf=float(chekey[flags].sum()),
                                        integer_TTL_expected_fp=float(Me@np.array(mem['integer_fpr'])),integer_Che_expected_fp=float(Mc@np.array(mem['integer_fpr'])),
                                        physical_build_s=build_s,ttl_count_s=ttl_sum_s,clock_replay_s=clock_s)
                    comparisons={}
                    for name in ('paper_M','exact_M'):
                        z={}
                        for cache,key in (('ttl','ttl_fp'),('clock','clock')):
                            bf=arms['h'][key] if cache=='ttl' else arms['h'][key]['fp'];rf=arms[name][key] if cache=='ttl' else arms[name][key]['fp']
                            z[cache]=dict(baseline_fp=bf,reweighted_fp=rf,raw_gain=1-rf/bf if bf else None,smoothed_ratio=(rf+1)/(bf+1))
                        comparisons[name]=z
                    row=dict(amplitude=amp,seed=seed,ttl=T,bf_bits_per_member=bpm,budget_bits=bits,stream_sha256=ah(stream),probability_sha256=ah(prob),
                             regional_probability=region_mass.tolist(),zipf_exponents=exponents.tolist(),paper_identity=pc,exact_identity=pe,arms=arms,comparisons=comparisons,
                             stream_prepare_s=stream_s,safe_prefix_s=safe_s,mass_prepare_s=M_s,ttl_prepare_s=ttl_prepare_s)
                    metadata['cases'].append(row);save(path,metadata)
                    print(f'CASE {ds} a={amp} seed={seed} T={T} bpm={bpm}: legal={pe["interior"]} gain={pe["predicted_gain"]} TTL={comparisons["exact_M"]["ttl"]["raw_gain"]} CLOCK={comparisons["exact_M"]["clock"]["raw_gain"]}',flush=True)
    assert len(metadata['cases'])==84;check();metadata.update(status='complete',wall_seconds=time.perf_counter()-start);save(path,metadata)
    print(f'COMPLETE {ds}:84 paired cases',flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=SETTINGS);p.add_argument('output',type=Path);a=p.parse_args();assert not a.output.exists()
    try:run(a.dataset,a.output)
    except Exception as e:save(a.output.with_suffix('.error.json'),dict(status='failed',error=repr(e)));raise
