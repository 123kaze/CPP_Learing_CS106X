from pathlib import Path
import numpy as np,subprocess,json
ROOT=Path(__file__).resolve().parents[1]
tmp=ROOT/'tmp'/'aqf-test';tmp.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(9257)
members=rng.integers(0,2**64,10000,dtype=np.uint64)
queries=rng.integers(0,2**64,50000,dtype=np.uint64)
stream=rng.integers(0,len(queries),1000000,dtype=np.int64)
for name,a in [('members',members),('queries',queries),('stream',stream)]:a.tofile(tmp/(name+'.bin'))
def wsl(path):return '/mnt/'+str(path.drive[0]).lower()+str(path)[2:].replace('\\','/')
cmd=['wsl','-d','Ubuntu-24.04','--',wsl(ROOT/'external'/'aqf_driver'),'32768',wsl(tmp/'members.bin'),wsl(tmp/'queries.bin'),wsl(tmp/'stream.bin'),'0',wsl(tmp/'output.json')]
r=subprocess.run(cmd,capture_output=True)
(ROOT/'evidence'/'aqf-native-test.log').write_bytes(r.stdout+b'\n'+r.stderr)
assert r.returncode==0,r.stderr[-1000:]
result=json.loads((tmp/'output.json').read_text())
assert result['feasible'] and result['filter_allocated_bytes']<=32768
assert result['fn_before']==result['fn_after']==0 and result['adaptations']>0
result.update(status='passed',test='synthetic correctness only, not research-dataset result',queries=len(stream))
(ROOT/'evidence'/'aqf-native-test.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
