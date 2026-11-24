"""Independent fullfile-inventory arithmetic and readonly database verification."""
from pathlib import Path
import json,sqlite3,hashlib,time
BLOOM=Path(__file__).resolve().parents[2];WR=BLOOM/'windows_research';ROOT=Path(__file__).resolve().parent

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    dest=ROOT/'verification.json';assert not dest.exists();t=time.perf_counter();r=WR/'round49_sis_inventory';m=json.loads((r/'results/inventory.json').read_text());old=json.loads((WR/'round48_sis_may_qualification/results/data.json').read_text());prefix=json.loads((r/'results/prefix_regression.json').read_text())
    assert m['status']=='complete' and m['exploratory_after_prefix_audit'] and not m['independent_holdout'] and not m['method_FP_measured'] and not m['model_AUC_measured']
    assert m['source_bytes']==13687894566 and m['source_sha256']==json.loads((WR/'round48_sis_extract_v2/results/extraction.json').read_text())['sha256']
    assert sum(m['status_counts'].values())==m['parsed_GET'] and m['parsed_GET']+sum(m['skipped'].values())==m['raw_lines']
    for code,count in m['status_counts'].items():assert sum(day.get(code,0) for day in m['daily_GET_status_counts'].values())==count
    assert m['retained_404_requests']+m['conflicting_404_requests']==m['status_counts']['404']
    assert m['members']+m['negative_keys']+m['conflicting_keys']==m['distinct_keys']
    assert prefix['source_prefix_sha256']==old['prefix_sha256'] and not json.loads((WR/'round48_sis_may_qualification/results/qualification.json').read_text())['eligible_for_method_comparison']
    for key in ('members','negative_keys','conflicting_keys','retained_404_requests','retained_success_requests','conflicting_404_requests'):assert prefix[key]==old[key]
    db=r/'cache/inventory.sqlite';assert sha(db)==m['db_sha256'];con=sqlite3.connect(f'file:{db}?mode=ro',uri=True);con.execute('PRAGMA query_only=ON')
    try:
        for flag,countfield,reqfield in ((1,'members','retained_success_requests'),(2,'negative_keys','retained_404_requests')):
            actual=con.execute('SELECT count(*),sum(successes+misses) FROM keys WHERE flags=?',(flag,)).fetchone()
            assert actual==(m[countfield],m[reqfield]);label='member' if flag==1 else 'negative';hist=m['frequency_bins'][label]
            assert sum(x['keys'] for x in hist)==m[countfield] and sum(x['requests'] for x in hist)==m[reqfield]
        assert con.execute('SELECT count(*) FROM keys WHERE first_seen>last_seen OR first_seen<0 OR last_seen>=?',(m['parsed_GET'],)).fetchone()[0]==0
        assert con.execute('PRAGMA quick_check').fetchone()==('ok',)
    finally:con.close()
    freeze=json.loads((r/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for p,h in freeze[group].items():assert sha(BLOOM/p)==h,p
    out=dict(status='verified',raw_lines=m['raw_lines'],GET_queries=m['parsed_GET'],members=m['members'],negative_keys=m['negative_keys'],retained_404_requests=m['retained_404_requests'],old_prefix_failure_unchanged=True,basic_fullfile_scale_passes=m['basic_fullfile_scale_passes'],full_method_qualification_done=False,FP_measured=False,models_trained=False,readonly_DB_check_passed=True,inventory_json_sha256=sha(r/'results/inventory.json'),db_sha256=m['db_sha256'],seconds=time.perf_counter()-t,verifier_sha256=sha(Path(__file__)))
    with dest.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
