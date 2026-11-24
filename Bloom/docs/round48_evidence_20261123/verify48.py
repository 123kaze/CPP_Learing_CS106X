"""Read-only SIS acquisition/qualification integrity and arithmetic audit."""
from pathlib import Path
import json,hashlib,time
import numpy as np
BLOOM=Path(__file__).resolve().parents[2];WR=BLOOM/'windows_research';ROOT=Path(__file__).resolve().parent


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    dest=ROOT/'verification.json';assert not dest.exists();start=time.perf_counter();r=WR/'round48_sis_may_qualification';extract=WR/'round48_sis_extract_v2'
    seen={}
    for p in (r/'plan/qualification-freeze.json',extract/'plan/freeze.json'):
        freeze=json.loads(p.read_text())
        for group in ('sources','inputs'):
            for rel,h in freeze[group].items():
                if rel not in seen:seen[rel]=sha(BLOOM/rel)
                assert seen[rel]==h,rel
    ex=json.loads((extract/'results/extraction.json').read_text());assert ex['status']=='verified' and ex['bytes']==13687894566 and ex['md5']=='dee4c55d036d6d1768a6f26a15b834c4' and not ex['old_partial_reused'] and not ex['other_months_extracted']
    assert json.loads((r/'results/extraction_failure.json').read_text())['error_type']=='TimeoutError'
    m=json.loads((r/'results/data.json').read_text());q=json.loads((r/'results/qualification.json').read_text());assert m['raw_lines']==m['raw_line_limit']==2000000 and not m['reached_EOF'] and not m['whole_month_analyzed']
    assert sum(m['status_counts'].values())==m['parsed_GET']==1946580
    assert m['status_counts']['404']==m['retained_404_requests']+m['conflicting_404_requests']==9940
    raw=extract/'cache/may/sis-log-201805-anonymous.txt';h=hashlib.sha256();size=0
    with raw.open('rb') as f:
        for i in range(2000000):
            line=f.readline(65537);assert line and len(line)<=65536;size+=len(line);h.update(line)
    assert size==m['prefix_bytes_read']==653207993 and h.hexdigest()==m['prefix_sha256']
    p=r/'cache/sis_may_prefix.npz';assert sha(p)==m['prepared_sha256']
    with np.load(p,allow_pickle=False) as d:
        y=d['y'];trace=d['trace'];order=d['order'];first=d['first'];boundary=int(d['boundary'])
        assert y.sum()==m['members']==140493 and (~y).sum()==m['negative_keys']==211
        assert int((~y[trace]).sum())==9940 and int(y[trace].sum())==m['retained_success_requests']
        assert boundary==m['parsed_GET']//4 and np.all(np.diff(order)>0) and int(order.max())<m['parsed_GET']
        assert len(np.unique(d['ids']))==len(y)
        for depth in (1,2):assert not d[f'prefix{depth}_reject'][y].any()
    reasons=[]
    for field,minimum in (('members',10000),('negative_keys',1000),('retained_404_requests',10000)):
        if m[field]<minimum:reasons.append(f'{field}<{minimum}')
    if m['retained_404_fraction']<.9:reasons.append('404retention<.9')
    diagnostics=[]
    for seed in (4801,4802,4803):
        s=json.loads((r/f'results/seed{seed}_diagnostic.json').read_text());assert s['status']=='complete'
        for field,minimum in (('train_negative_keys',20),('validation_negative_keys',20),('learning_queries',1000),('tail_queries',1000)):
            if s[field]<minimum:reasons.append(f'seed{seed}:{field}<{minimum}')
        diagnostics.append({key:s[key] for key in ('seed','train_negative_keys','validation_negative_keys','learning_queries','tail_queries','development_auc16')})
    assert reasons==q['ineligibility_reasons'] and not q['eligible_for_method_comparison'] and not q['method_FP_evaluated']
    out=dict(status='verified',sources_and_inputs_checked=len(seen),prefix_lines=2000000,prefix_bytes=size,members=140493,negative_keys=211,negative_requests=9940,qualification_passed=False,reasons=reasons,diagnostics=diagnostics,original_timeout_preserved=True,partial_data_used=False,other_months_opened=False,method_FP_run=False,old_outputs_changed=False,third_party_execution=False,seconds=time.perf_counter()-start,verifier_sha256=sha(Path(__file__)))
    with dest.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
