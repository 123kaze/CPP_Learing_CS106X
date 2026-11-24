"""Explicitly reuse 38 completed v2 cases; leave new pilot filenames empty for v4 regression."""
import sys,os,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
OLD=WR/'round53_index_free_recheck_v2'


def main():
    assert not (ROOT/'results/reuse_provenance.json').exists()
    for version in ('round53_index_free_recheck_v2','round53_index_free_recheck_v3'):
        f=json.loads((WR/version/'plan/freeze.json').read_text())
        for p,h in f['sources'].items():assert sha(BLOOM/p)==h,p
    (ROOT/'cache').mkdir(parents=True,exist_ok=True)
    files=[];prepared=[];workers=[]
    def copy(rel):
        p=OLD/rel;q=ROOT/rel;assert p.is_file() and not q.exists()
        q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
        h=sha(p);assert sha(q)==h
        files.append(dict(path=rel,source=str(p.relative_to(BLOOM)),sha256=h))
    for ds in DATASETS:
        if ds!='shalla':
            p=OLD/f'cache/{ds}.npz';q=ROOT/f'cache/{ds}.npz'
            meta=json.loads((OLD/f'results/raw_{ds}.json').read_text())
            assert sha(p)==meta['prepared_sha256'] and not q.exists()
            os.link(p,q)
            prepared.append(dict(path=str(q.relative_to(ROOT)),source=str(p.relative_to(BLOOM)),sha256=meta['prepared_sha256'],sharing='immutable input hardlink; never written'))
            copy(f'results/raw_{ds}.json');copy(f'results/raw_{ds}_process.json')
        if ds in ('caida','shalla'):continue
        for kib in BUDGETS[ds]:
            w=json.loads((OLD/f'results/{ds}_{kib}.json').read_text())
            assert w['status']=='complete' and w['peak_rss_bytes']<4*1024**3
            workers.append(dict(dataset=ds,budget_kib=kib,cases=len(w['workloads']),rows=len(w['rows'])))
            copy(f'results/{ds}_{kib}.json');copy(f'results/{ds}_{kib}_process.json')
    assert sum(w['cases'] for w in workers)==38 and sum(w['rows'] for w in workers)==266
    save(ROOT/'results/reuse_provenance.json',dict(status='verified',reused_cases=38,reused_rows=266,new_cases=24,new_rows=168,reused_workers=workers,files=files,prepared_inputs=prepared,change='Frozen v3 worker under scoped release of unused q_region workspace; no cache/selector/input algorithm changes',pilots='New v4 pilot outputs must match the original completed v2 cases before continuation',original_failures=[str((WR/v/'results/failure.json').relative_to(BLOOM)) for v in ('round53_index_free_recheck_v2','round53_index_free_recheck_v3')]))
    print('REUSE_VERIFIED 38 cases / 266 rows',flush=True)


if __name__=='__main__':main()
