"""Measure native minimum structure allocation without inserting/querying."""
import json,subprocess
import engine as E
from run_aqf import wsl
def run(datasets=('cod','caida','shalla','url','caida_flow','mawi2021_flow')):
    rows=[]
    for ds in datasets:
        folder=E.ROOT/'tmp'/('aqf_'+ds);folder.mkdir(parents=True,exist_ok=True)
        if not (folder/'members.bin').exists():
            s,_,_=E.load(ds);s.h1m.tofile(folder/'members.bin')
        empty=folder/'empty.bin';empty.write_bytes(b'')
        out=folder/'minimum-allocation.json'
        command=['wsl','-d','Ubuntu-24.04','--',wsl(E.ROOT/'external'/'aqf_driver'),'0',wsl(folder/'members.bin'),wsl(empty),wsl(empty),'0',wsl(out)]
        subprocess.run(command,check=True,capture_output=True)
        obj=json.loads(out.read_text());minimum=obj['minimum_allocated_bytes']
        for kib in E.BUDGETS[ds]:rows.append(dict(dataset=ds,budget_kib=kib,minimum_native_filter_bytes=minimum,
            native_allocation_fits=minimum<=kib*1024,construction_and_adaptation_not_yet_checked=True))
        print('AQF MINIMUM',ds,minimum,flush=True)
    target=E.ROOT/'results'/'aqf_preflight.json'
    if target.exists():rows=json.loads(target.read_text())['rows']+rows
    E.save(target,dict(rows=rows,completed=True,scope='Minimum actual upstream QF allocation for initial <=90% load and remainder2..24. Allocation feasibility does not guarantee collision-extension capacity. Reverse map excluded and reported separately in actual runs.'))
if __name__=='__main__':
    import sys
    run(tuple(sys.argv[1:]) or ('cod','caida','shalla','url','caida_flow','mawi2021_flow'))
