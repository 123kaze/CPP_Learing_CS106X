"""Reuse frozen full-matrix arithmetic, adding explicit v2/v4 provenance and timing scopes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
import frozen53
_original=frozen53.load('report53')
assert _original.ROOT==ROOT
compare_pilot=_original.compare_pilot


def run():
    _original.run()
    path=ROOT/'results/verification.json';v=json.loads(path.read_text())
    v.pop('new_v3_cases',None);v.pop('new_v3_rows',None)
    v.update(new_v4_cases=24,new_v4_rows=168,workspace_equivalence_cases=4,workspace_equivalence_rows=28)
    timing={}
    for group,datasets in (('v2_reused',[ds for ds in DATASETS if ds not in ('caida','shalla')]),('v4_new',['caida','shalla'])):
        ratios=[]
        for ds in datasets:
            for kib in BUDGETS[ds]:
                w=json.loads((ROOT/f'results/{ds}_{kib}.json').read_text())
                for name,_ in workloads(ds):
                    r={x['method']:x for x in w['rows'] if x['workload']==name}
                    ratios.append(r['Replay']['selection_build_s']/r['RA-PLBF-GT19']['selection_build_s'])
        timing[group]=dict(cases=len(ratios),median_paired_selection_speedup=float(np.median(ratios)))
    v['selection_timing_by_implementation']=timing
    v['selection_timing_note']='Paired single-run selection/build timings: 38 reused v2 cases and 24 workspace-optimized v4 cases. Pooled median mixes workspace versions; neither includes retraining or service inference/backend latency.'
    save(path,v)
    p=ROOT/'README.md';text=p.read_text()
    beginning=text.index('**版本与复用说明：**');ending=text.index('完整执行62case',beginning)
    text=text[:beginning]+('**版本与复用说明：** v1原始地址编码资格失败；v2完成38case后触发4GiB上限；用户授权的v3又触发6GiB上限。用户再次明确同意后，v4仅释放候选中后续不使用的逐查询q_region工作区，保留6GiB上限。先用固定4case/28方法行核验所有非计时字段与v2一致，再完成CAIDA静态/Shalla剩余24case。原38case/266行逐字节复用，不冒充重跑；原失败全部保留。\n\n[复用来源](results/reuse_provenance.json) · [工作区等价核验](results/workspace_equivalence.json)\n\n')+text[ending:]
    text+='\n## 选择计时版本说明\n\n整体选择时间中位比混合了v2与v4工作区实现，不把它当单一实现的完整构建加速。各case内两方法使用相同版本；输入读取、JIT、模型训练/服务查询的边界仍需保留。\n\n'
    for group,info in timing.items():text+=f"- {group}：{info['cases']}case，Replay/RA选择＋构建时间配对中位{info['median_paired_selection_speedup']:.3f}×。\n"
    p.write_text(text)


if __name__=='__main__':run()
