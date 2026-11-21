"""Pre-experiment fixed-cost forecasts from round31, stdlib only. Not measured speedups."""
from pathlib import Path
import csv,json,hashlib
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent
DATASETS=('cod','url','caida','shalla','caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow')
DELAYS=(0,5,10,25,50,100)


def compute():
    path=WR/'round31_sqlite_online/results/medians.csv'
    with path.open() as f:rows=list(csv.DictReader(f))
    points=[];thresholds=[];sources={str(path.relative_to(WR.parent)):hashlib.sha256(path.read_bytes()).hexdigest()}
    for ds in DATASETS:
        source=WR/f'round31_sqlite_online/results/{ds}.json';d=json.loads(source.read_text());assert d['status']=='complete'
        sources[str(source.relative_to(WR.parent))]=hashlib.sha256(source.read_bytes()).hexdigest();N=d['queries']
        methods={r['method']:r for r in rows if r['dataset']==ds and r['backend']=='file'};a,b=methods['RA6'],methods['BF+Cache']
        ta,tb=float(a['median_us']),float(b['median_us']);ca,cb=int(a['backend_calls']),int(b['backend_calls'])
        threshold=(ta-tb)*N/(cb-ca) if cb>ca else None
        thresholds.append(dict(dataset=ds,RA_us=ta,BF_us=tb,RA_backend_calls=ca,BF_backend_calls=cb,queries=N,extra_us_break_even=threshold))
        for delay in DELAYS:
            pa,pb=ta+ca/N*delay,tb+cb/N*delay
            points.append(dict(dataset=ds,extra_us=delay,predicted_RA_us=pa,predicted_BF_us=pb,predicted_RA_BF_ratio=pa/pb,predicted_RA_faster=pa<pb))
    return dict(status='prediction_only_not_measurement',source_hashes=sources,thresholds=thresholds,points=points,
                forecast_wins_by_extra_us={str(x):sum(r['predicted_RA_faster'] for r in points if r['extra_us']==x) for x in DELAYS})


if __name__=='__main__':
    d=compute();dest=ROOT/'results/pretrial_forecast.json';dest.parent.mkdir(exist_ok=True)
    text=json.dumps(d,indent=2)+'\n'
    if dest.exists():assert dest.read_text()==text,'Refuse changing frozen prediction'
    else:dest.write_text(text)
    print(json.dumps(d['forecast_wins_by_extra_us'],indent=2))
