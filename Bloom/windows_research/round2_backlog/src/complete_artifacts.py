"""After all experiments, verify then create the report and figures for QA."""
import time,sys,subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
while not (ROOT/'results'/'EXPERIMENTS_COMPLETE.json').exists():time.sleep(10)
for name,script in [('integrity-and-results','verify_round2.py'),('report','build_report.py'),('figures','make_figures.py')]:
    status=ROOT/'results'/'artifacts-phase.json'
    status.write_text(json.dumps(dict(stage=name,status='running')),encoding='utf-8')
    with (ROOT/'results'/f'final-{name}.log').open('w',encoding='utf-8') as f:
        result=subprocess.run([sys.executable,'-u','src/'+script],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode:
        status.write_text(json.dumps(dict(stage=name,status='failed',returncode=result.returncode)),encoding='utf-8');raise RuntimeError(script)
(ROOT/'results'/'FIGURES_READY.json').write_text(json.dumps(dict(status='awaiting_visual_qa',figures=['causal_trace_fpr.png','model_grid_fp.png','end_to_end.png'])),encoding='utf-8')
status.write_text(json.dumps(dict(stage='report_and_figures_created',status='passed',remaining='visual QA')),encoding='utf-8')
