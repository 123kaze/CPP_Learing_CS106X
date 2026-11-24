import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from stability51 import *
import csv,statistics


def report():
    check();workers=[json.loads((ROOT/f'results/seed{s}.json').read_text()) for s in (5001,5002,5003)];assert all(w['status']=='complete' and len(w['rows'])==4 for w in workers)
    rows=[dict(seed=w['seed'],**r) for w in workers for r in w['rows']]
    with (ROOT/'results/rows.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    gates=[]
    for w in workers:
        rr={r['recipe']:r for r in w['rows']};a=rr['balanced_clip'];old=rr['original'];good=a['development_auc']>=.7 and a['development_auc']-old['development_auc']>=.03 and a['finite_scores']
        gates.append(dict(seed=w['seed'],original_auc=old['development_auc'],balanced_clip_auc=a['development_auc'],gain=a['development_auc']-old['development_auc'],passes=good))
    result=dict(status='verified',models=12,original_AUC_regressions=3,chosen_recipe_if_gate_passes='balanced_clip',gate_passes=sum(g['passes'] for g in gates)>=2,seed_gates=gates,not_best_of_four_selection=True,method_FP_measured=False,independent_holdout=False,worker_sha256={f'seed{w["seed"]}.json':sha(ROOT/f'results/seed{w["seed"]}.json') for w in workers})
    save(ROOT/'results/verification.json',result)
    text=['# Round51：训练稳定性开发消融','','新训练配方探索，原结果不变。只看开发AUC和数值稳定性，未测实体FP；预选候选固定balanced_clip，不从四个配方事后挑最高AUC。','','| recipe | AUC中位 | member bin999比例中位 | member占用segment数中位 | rawscore范围（所有seed） |','| --- | ---: | ---: | ---: | --- |']
    for recipe in RECIPES:
        r=[x for x in rows if x['recipe']==recipe];text.append(f'| {recipe} | {statistics.median(x["development_auc"] for x in r):.6f} | {statistics.median(x["member_fraction_bin999"] for x in r):.6f} | {statistics.median(x["member_occupied_bins"] for x in r)} | {min(x["raw_score_min"] for x in r):.6f} .. {max(x["raw_score_max"] for x in r):.6f} |')
    text+=['',f'进入后续实体方法比较的开发闸门：{result["gate_passes"]}。', '', 'Balanced使用每类相等总权重、平均样本weight1，不移除或复制训练keys。Clip使用max_delta_step1及lr.1，rawscore相对实际weighted prior的累计变化界核验通过。没有翻转score/标签，没有用tail FP挑配方，没有改stream、预算或旧Frozen算法。','','后续若执行，必须同时给Gama/Replay/RA-global/RA相同新配方，原配方作为完整控制，BF不付不需要的模型成本；平衡权重属于新的训练variant，不能改名旧RA6/Gama已获得相同保证或旧holdout。','','开发AUC改善不等于端到端或BF+Cache胜出。真实文件整体负请求比例低、热点和冷新key不同、训练过程有成本，都仍需完整对照。当前SIS source已做过探索性inventory/diagnostic，不是独立真实holdout。论文未动，未push。','']
    with (ROOT/'results/report.md').open('x') as f:f.write('\n'.join(text))
    check();print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':report()
