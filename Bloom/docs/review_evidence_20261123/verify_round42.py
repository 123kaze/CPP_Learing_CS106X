"""Independent final-cache all-member verification; no SQL timing or archive overwrite."""
import sys
from pathlib import Path
BLOOM=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(BLOOM/'windows_research/round42_raw_key_sqlite/src'))
import worker42 as R
import json,time,hashlib
np=R.np


def main():
    output=HERE/'round42_final_cache_verification.json';assert not output.exists();start=time.perf_counter();R.check();checks=[];sources={}
    for seed in (3601,3602,3603):
        s,X,learn,tail,keys,blob,offsets,requests,learning,hashes,scores,index,lm,qblob,qoff,prep=R.prepare(seed)
        p=R.ROOT/f'results/seed{seed}.json';record=json.loads(p.read_text());sources[str(p.relative_to(BLOOM))]=hashlib.sha256(p.read_bytes()).hexdigest();assert record['status']=='complete'
        ref41=json.loads((R.WR/f'round41_exact_key_budget/results/seed{seed}.json').read_text())['rows']
        for kib in (8,16,32):
            candidates,_=R.selection(s,scores,lm,learn,tail,index,qblob,qoff,kib,ref41)
            for method in R.METHODS:
                c=candidates.get(method)
                mode='prefix' if method=='RA6-prefix' else 'direct' if method=='DirectHashIndex' else 'exact'
                flt=None if method=='NoFilter' else R.Filter(c,s,scores,mode,index)
                accepted,found,data=R.reference_for(flt,c,requests,s,hashes,blob,offsets,index)
                rows=[r for r in record['timings'] if r['method']==method and r['budget_kib']==kib];assert len(rows)==3
                for row in rows:
                    assert row['accepted_mask_sha256']==R.W.ah(accepted) and row['found_mask_sha256']==R.W.ah(found)
                    assert row['cache_sha256']==(R.W.ah(data) if flt else None)
                before=R.W.ah(data);hits=0
                if flt is not None and flt.cache_bytes:
                    spec=flt.spec
                    if mode=='exact':hits=int(R.E.member_hits(data,hashes,blob,offsets,np.flatnonzero(s.y),spec['buckets']))
                    else:hits=int(R.K.count_member_hits(data,s.h1m,spec['buckets'],40,spec['Q'],spec['ob'],spec['slot_bits'],4))
                assert hits==0 and before==R.W.ah(data)
                checks.append(dict(seed=seed,budget_kib=kib,method=method,members_checked=len(s.h1m),all_member_final_cache_hits=hits,all_three_archived_masks_equal=True,all_three_archived_caches_equal=True))
        print('FINAL_CACHE_VERIFIED',seed,flush=True)
    assert len(checks)==63;R.check()
    with output.open('x') as f:json.dump(dict(status='verified',checks=checks,seconds=time.perf_counter()-start,sources=sources,verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),sql_timings_rerun=False,frozen_outputs_changed=False),f,indent=2);f.write('\n')
    print('All63 final caches reconstructed; all189 query masks/cache hashes matched; zero final-member cache hits.')

if __name__=='__main__':main()
