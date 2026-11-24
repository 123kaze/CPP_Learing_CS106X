"""Explicit provenance-preserving import of completed v2 results; never claim they were rerun."""
import sys,os,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
OLD=WR/'round53_index_free_recheck_v2'


def main():
    assert not (ROOT/'results/reuse_provenance.json').exists()
    frozen=json.loads((OLD/'plan/freeze.json').read_text())
    for p,h in frozen['sources'].items():assert sha(BLOOM/p)==h,p
    for name in ('common53.py','cache53.py','prepare53.py','test53.py'):
        assert (ROOT/'src'/name).read_bytes()==(OLD/'src'/name).read_bytes(),name
    assert (ROOT/'src/worker53.py').read_text().replace("assert out['peak_rss_bytes']<6*1024**3;save(dest,out)","assert out['peak_rss_bytes']<4*1024**3;save(dest,out)")==(OLD/'src/worker53.py').read_text()
    files=[];reused=[];inputs=[]
    def copy(rel):
        p=OLD/rel;q=ROOT/rel;assert p.is_file() and not q.exists()
        q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
        h=sha(p);assert sha(q)==h
        files.append(dict(path=rel,source=str(p.relative_to(BLOOM)),sha256=h))
    for ds in DATASETS:
        if ds!='shalla':
            p=OLD/f'cache/{ds}.npz';q=ROOT/f'cache/{ds}.npz';meta=json.loads((OLD/f'results/raw_{ds}.json').read_text())
            assert sha(p)==meta['prepared_sha256'] and not q.exists()
            os.link(p,q)  # immutable prepared input only; no process writes these files
            inputs.append(dict(path=str(q.relative_to(ROOT)),source=str(p.relative_to(BLOOM)),sha256=meta['prepared_sha256'],sharing='hardlink immutable input'))
            copy(f'results/raw_{ds}.json');copy(f'results/raw_{ds}_process.json')
        if ds in ('caida','shalla'):continue
        for kib in BUDGETS[ds]:
            w=json.loads((OLD/f'results/{ds}_{kib}.json').read_text());assert w['status']=='complete' and w['peak_rss_bytes']<4*1024**3
            reused.append(dict(dataset=ds,budget_kib=kib,cases=len(w['workloads']),rows=len(w['rows'])))
            copy(f'results/{ds}_{kib}.json');copy(f'results/{ds}_{kib}_process.json')
    for name in ('pilot_url_64','pilot_caida_flow_16'):
        copy(f'results/{name}.json');copy(f'results/{name}_process.json')
    copy('results/pilot_gate.json')
    assert sum(r['cases'] for r in reused)==38 and sum(r['rows'] for r in reused)==266
    save(ROOT/'results/reuse_provenance.json',dict(status='verified',reused_cases=38,reused_rows=266,new_cases=24,new_rows=168,reused_workers=reused,files=files,prepared_inputs=inputs,worker_difference='RSS postcondition only: 4GiB -> 6GiB',algorithm_input_and_cache_sources_byte_identical=True,pilots='original v2 pilots reused, not rerun',original_failure=str((OLD/'results/failure.json').relative_to(BLOOM))))
    print('REUSE_VERIFIED',38,'cases',266,'rows',flush=True)


if __name__=='__main__':main()
