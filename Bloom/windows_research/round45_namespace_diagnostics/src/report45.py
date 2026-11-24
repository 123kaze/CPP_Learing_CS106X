import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from namespace45 import ROOT,D,check,sha,save
import json,statistics,csv


def report():
    check();workers=[json.loads((ROOT/f'results/{c}.json').read_text()) for c in D.CLUSTERS];assert all(w['status']=='complete' and len(w['rows'])==12 for w in workers)
    rows=[dict(cluster=w['cluster'],**r) for w in workers for r in w['rows']]
    with (ROOT/'results/development.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader()
        for r in rows:writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in r.items()})
    groups=[]
    for w in workers:
        lookup={(r['seed'],r['representation']):r for r in w['rows']}
        medians={rep:statistics.median(lookup[s,rep]['development_auc'] for s in D.SEEDS) for rep in ('lexical24','key_size25','prefix88','combined89')}
        delta=statistics.median(lookup[s,'combined89']['development_auc']-lookup[s,'lexical24']['development_auc'] for s in D.SEEDS)
        groups.append(dict(cluster=w['cluster'],median_auc=medians,median_paired_combined_gain=delta,passes_development_gate=(delta>=.03 and medians['combined89']>=.65)))
    passed=sum(g['passes_development_gate'] for g in groups)>=2
    result=dict(status='verified',models=36,old_development_AUC_regressions=9,groups=groups,advance_to_unseen_clusters=passed,gate='atleast2of3clusters median paired gain>=.03 and combined median AUC>=.65',tail_FP_evaluated=False,new_clusters_opened=False,not_an_independent_holdout=True,worker_hashes={f'{w["cluster"]}.json':sha(ROOT/f'results/{w["cluster"]}.json') for w in workers})
    save(ROOT/'results/verification.json',result)
    text=['# Round45：已知样本的开发段表示诊断','','明确事后探索，不是新独立holdout。36个固定16tree模型，9个原AUC回归通过。只使用train建立prefix词表，原key_size为请求元数据，不是response value_size。未测任何tail方法FP，未打开cluster004–006。','','| cluster | 原24维AUC中位 | +key_size | +prefix | 合并 | 配对增量中位 | 通过预设门槛 |','| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for g in groups:
        a=g['median_auc'];text.append(f'| {g["cluster"]} | {a["lexical24"]:.6f} | {a["key_size25"]:.6f} | {a["prefix88"]:.6f} | {a["combined89"]:.6f} | {g["median_paired_combined_gain"]:.6f} | {g["passes_development_gate"]} |')
    text+=['',f'整体开发闸门：{passed}。至少2/3cluster增量>=.03且AUC>=.65；不调整阈值。','', 'Prefix词表固定336Bpayload+ndarray header（本环境总448B），不能免费给learned方法；后续若进入BF比较必须将词表计入每个learned候选的预算，BF无需承担此项。此轮只有区分度诊断，不证明FP、延迟、训练或整体部署获胜。原始key_size在匿名化数据里由querymetadata提供，不能把查全局key字典的成本藏起来。','','开发样本此前看过tail，任何表示选择都属于探索。只有另冻规则后未看过数据上的完整结果才可作为后续验证；不能把反复试验的第一个正例直接当确认性证据。原任务仍是静态检查点目录，不是原生产backendNotFound。','']
    with (ROOT/'results/report.md').open('x') as f:f.write('\n'.join(text))
    check();print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':report()
