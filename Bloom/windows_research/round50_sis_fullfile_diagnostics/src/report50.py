import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare50 import *
import csv,statistics


def report():
    check();meta=json.loads((ROOT/'results/preparation.json').read_text());inv=json.loads((WR/'round49_sis_inventory/results/inventory.json').read_text());rows=[json.loads((ROOT/f'results/seed{s}.json').read_text()) for s in SEEDS];assert all(r['status']=='complete' for r in rows)
    reasons=list(inv['basic_scale_failure_reasons'])
    for r in rows:
        for field,minimum in (('train_negative_keys',20),('validation_negative_keys',20),('learning_queries',1000),('tail_queries',1000)):
            if r[field]<minimum:reasons.append(f'seed{r["seed"]}:{field}<{minimum}')
    result=dict(status='verified',eligible_for_method_comparison=not reasons,reasons=reasons,known_exploration_file=True,independent_holdout=False,old_round48_failure_unchanged=True,method_FP_measured=False,metadata=meta,diagnostics=rows)
    save(ROOT/'results/qualification.json',result)
    with (ROOT/'results/diagnostics.csv').open('x',newline='') as f:
        fields=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    text=['# Round50：已知完整SIS文件的开发诊断','','这是第48/49轮之后的新探索，不是独立holdout，不倒填旧prefix资格。全文件只代表其实际2018-05-23至31日范围；observed HTTPsuccess/404不能证明业务record存在性。','','| seed | member train | negative train/val | learning/tail negatives | AUC16 | 1000分段中的member/valnegative占用数 | tail未见key请求比例 |','| --- | ---: | --- | --- | ---: | --- | ---: |']
    for r in rows:
        s=r.get('segment_resolution',{});text.append(f'| {r["seed"]} | {r["train_members"]} | {r["train_negative_keys"]}/{r["validation_negative_keys"]} | {r["learning_queries"]}/{r["tail_queries"]} | {r["development_auc16"]} | {s.get("member_occupied_bins")}/{s.get("validation_negative_occupied_bins")} | {r["tail_unseen_query_fraction"]} |')
    text+=['',f'规模/split资格：{not reasons}；原因：{reasons}。','', 'AUC和16tree score分辨率分开看。极不平衡训练可能导致sigmoid分数集中；本轮不翻转score、不改classweights/样本比例。16tree诊断不能代表整个200tree候选网格已退化或已经成功。便宜path支持规则、重叠、region重复差和完整分项时间在JSON/CSV。','','只保留negative流及其原GETordinal，完整source行数/GET数/SHA与第49轮匹配；没有人为增加negative或重排时间。未来严格精确negativecache中member查询不会命中或插入，不改变CLOCK状态；这解释FP诊断可用negative-only流，但它不是完整query延迟计时，也不意味着可以把positive比例隐藏。','','原rawkey blob、输入X/ids/工作SQLite都是offline输入/准备工作区，不算免费的部署Filter。没有建立prefix验证memberhash索引；若后续用Exact128必须完整计费并保持static版本保证。','','本轮未构造选择五方法、更未测后端服务时间，因此没有RA胜出结论。开发诊断完成后，任何新比较须另冻协议；原source/计数/失败不覆盖，论文未动，未push。','']
    with (ROOT/'results/report.md').open('x') as f:f.write('\n'.join(text))
    check();print('FULLFILE_DIAGNOSTICS_VERIFIED',not reasons,reasons,flush=True)

if __name__=='__main__':report()
