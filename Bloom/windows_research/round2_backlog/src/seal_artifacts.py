"""Run after human/model image inspection; seal the finished deliverables."""
from pathlib import Path
import json,hashlib,datetime,argparse
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    p=argparse.ArgumentParser();p.add_argument('--visual-qa-passed',action='store_true');a=p.parse_args();assert a.visual_qa_passed
    v=json.loads((ROOT/'results'/'verification.json').read_text(encoding='utf-8'));assert v['status']=='passed'
    images=['causal_trace_fpr.png','model_grid_fp.png','end_to_end.png']
    assert all((ROOT/'figures'/name).exists() for name in images)
    frozen=json.loads((ROOT/'plan'/'final-holdout-freeze.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/f)==h for f,h in frozen['operational_source_sha256'].items())
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    qa=dict(status='passed',reviewed_utc=now,images=images,method='Assistant inspected all three rendered images through view_image for clipping, axes, labels and consistency with source data')
    (ROOT/'evidence'/'figure-visual-qa.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
    rpath=ROOT/'results'/'REPORT_COMPLETE.json';r=json.loads(rpath.read_text(encoding='utf-8'));r['figure_visual_qa']='passed';rpath.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    done=dict(completed_utc=now,experiments=26,excluded='C1-C5 and non-experimental tasks',verification='passed',figure_visual_qa='passed',counts=v['counts'],report='REPORT.md',protected_folders_unchanged=v['protected']['unchanged'])
    (ROOT/'results'/'ALL_COMPLETE.json').write_text(json.dumps(done,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'results'/'artifacts-phase.json').write_text(json.dumps(dict(stage='complete',status='passed',figure_visual_qa='passed')),encoding='utf-8')
    (ROOT/'results'/'final-phase.json').write_text(json.dumps(dict(stage='complete',status='passed',verification='results/verification.json',report='REPORT.md')),encoding='utf-8')
    (ROOT/'results'/'FIGURES_READY.json').write_text(json.dumps(dict(status='passed',visual_qa='evidence/figure-visual-qa.json')),encoding='utf-8')
    files=[ROOT/'REPORT.md']
    for pattern in ('src/*.py','src/*.cpp','plan/*.md','plan/*.json','results/**/*.json','tables/*.csv','figures/**/*.csv','figures/*.png','figures/*.svg','figures/*.md','evidence/**/*.json'):
        files.extend(f for f in ROOT.glob(pattern) if 'invalid_' not in str(f) and f.name!='deliverable-sha256.json')
    manifest={str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in sorted(set(files))}
    (ROOT/'evidence'/'deliverable-sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(done,ensure_ascii=False),flush=True)
if __name__=='__main__':run()
