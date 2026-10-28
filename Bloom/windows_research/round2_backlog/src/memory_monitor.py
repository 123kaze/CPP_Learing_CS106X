"""Observe process-lifetime peak RSS of this suite, separate from filter state."""
from pathlib import Path
import time,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
rows={}
for _ in range(7200):
    command="Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and $_.CommandLine -match 'run_main.py|run_stacked.py|run_ablation.py|run_aqf.py' } | Select-Object ProcessId,CommandLine,PeakWorkingSetSize,WorkingSetSize | ConvertTo-Json -Compress"
    r=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True)
    try:data=json.loads(r.stdout) if r.stdout.strip() else []
    except ValueError:data=[]
    if isinstance(data,dict):data=[data]
    for value in data:
        key=str(value['ProcessId']);previous=rows.get(key,{})
        value['observed_peak_bytes']=max(previous.get('observed_peak_bytes',0),int(value.get('PeakWorkingSetSize',0))*1024,int(value.get('WorkingSetSize',0)))
        rows[key]=value
    (ROOT/'evidence'/'process-memory-peaks.json').write_text(json.dumps(dict(scope='Observed process lifetime RSS, including candidates/data/interpreter; not filter resident bytes or an isolated phase measurement',processes=list(rows.values())),indent=2),encoding='utf-8')
    if (ROOT/'results'/'ALL_COMPLETE.json').exists():break
    time.sleep(10)
