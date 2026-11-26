"""Complete-matrix checks and results; no changes to experiment selection or outputs."""
import sys,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shared54 import *
from audit54 import writecsv


def compare(rows,method,baseline,keys):
    a={tuple(r[k] for k in keys):r for r in rows if r['method']==method};b={tuple(r[k] for k in keys):r for r in rows if r['method']==baseline};assert set(a)==set(b)
    pairs=[(a[k],b[k]) for k in a];ratio=[(x['fp']+1)/(y['fp']+1) for x,y in pairs]
    worst=max(zip(ratio,pairs),key=lambda x:x[0]);x,y=worst[1]
    return dict(cases=len(pairs),wins=sum(x['fp']<y['fp'] for x,y in pairs),ties=sum(x['fp']==y['fp'] for x,y in pairs),losses=sum(x['fp']>y['fp'] for x,y in pairs),median_smoothed_ratio=float(np.median(ratio)),FP_sum=sum(x['fp'] for x,y in pairs),baseline_FP_sum=sum(y['fp'] for x,y in pairs),worst=dict(case={k:x[k] for k in keys},FP=x['fp'],baseline_FP=y['fp'],smoothed_ratio=worst[0]))


def main():
    check();start=time.perf_counter();zs=[];cs=[];nums=[];os=[];config={};raw=[]
    for p in sorted((ROOT/'results').glob('zero_*.json')):
        w=json.loads(p.read_text());assert w['status']=='complete';zs+=w['rows'];raw.append(w)
    for ds in CMATRIX:
        w=json.loads((ROOT/f'results/coupled_{ds}.json').read_text());assert w['status']=='complete';cs+=w['rows'];nums+=w['numerics'];raw.append(w)
        assert len(w['cases'])==8 and all(c['histograms_equal'] and c['prediction_inputs_bit_equal'] for c in w['cases'])
        for kib in CMATRIX[ds]:
            rr=[r for r in w['rows'] if r['budget_kib']==kib and r['method']=='RA-stage2'];assert len(rr)==4
            assert len({(r['trees'],r['frac'],r['flags_sha']) for r in rr})==1
    for ds in DMATRIX:
        w=json.loads((ROOT/f'results/online_{ds}.json').read_text());assert w['status']=='complete';os+=w['rows'];raw.append(w);config[ds]={r['method']:r for r in w['configuration']}
    assert len(zs)==186 and len(cs)==168 and len(nums)==6 and len(os)==1071
    for w in raw:assert w['peak_rss_bytes']<4*1024**3
    for r in zs+cs:assert r['member_fn']==0 and r['deployment_used_bytes']<=r['deployment_M'] and r['required_backend_member_index_bytes']==0
    for r in os:assert r['member_fn']==0 and r['queries']==5000
    writecsv(ROOT/'results/zero_rows.csv',zs);writecsv(ROOT/'results/order_rows.csv',cs);writecsv(ROOT/'results/query_rows.csv',os)
    zsummary={}
    for cohort,subset in [('all',zs),('TCP',[r for r in zs if '_tcp_' in r['dataset']]),('Clark',[r for r in zs if r['dataset']=='clark']),('URL_no_repeat_adversarial',[r for r in zs if r['dataset']=='url'])]:
        zsummary[cohort]={}
        for m in ('RA6','RA6-Z-predictive','RA6-ZGate'):
            v=compare(subset,m,'BF',('dataset','seed','budget_kib','workload'));v['zero_selected']=sum(r['trees']==0 for r in subset if r['method']==m);zsummary[cohort][m]=v
    stage={m:compare(cs,m,'h-Replay',('dataset','budget_kib','order')) for m in ('RA-stage1','RA-stage2','weighted-Replay','weighted-ZReplay')}
    numerical=[]
    for r in nums:
        iteration3=next(x for x in r['iterations'] if x['iteration']==3)
        numerical.append(dict(dataset=r['dataset'],budget_kib=r['budget_kib'],epsilon_residual3=iteration3['epsilon_next_residual_inf'],objective_residual3=iteration3['objective_next_relative_change'],pass3=iteration3['passes_both_residual_thresholds'],SA_reference_gap=r['numerical_SA_grid_objective']['gap3_over_best'],FA_reference_gap=r['numerical_FA_direct_objective']['gap3_over_best'],global_optimality_certified=False,any_two_cycle=any(x['possible_two_cycle'] for x in r['iterations']),optimizer_failures=sum(not x['success'] for target in ('numerical_SA_grid_objective','numerical_FA_direct_objective') for x in r[target]['local_runs'])))
    latency=[];cost=[]
    for ds in DMATRIX:
        pvalues=sorted({r['member_fraction'] for r in os if r['dataset']==ds})
        for p in pvalues:
            for target in (3,37,100):
                cells={m:[r for r in os if r['dataset']==ds and r['member_fraction']==p and r['target_backend_us']==target and r['method']==m] for m in ('Gama','Replay','RAglobal','RA6','BF','PlainBF','NoFilter')}
                for m,rr in cells.items():
                    assert len(rr)==3 and len({(r['request_sha'],r['calls'],r['fp'],r['cache_sha'],r['found_sha']) for r in rr})==1
                    us=np.array([r['ns_per_query']/1000 for r in rr]);base=np.array([r['ns_per_query']/1000 for r in cells['BF']])
                    latency.append(dict(dataset=ds,member_fraction=p,target_backend_us=target,method=m,median_us=float(np.median(us)),min_us=float(us.min()),max_us=float(us.max()),throughput_queries_s=1e6/float(np.median(us)),paired_ratio_vs_BF=float(np.median(us/base)),backend_calls=rr[0]['calls'],negative_FP=rr[0]['fp']))
                for baseline in ('BF','Replay','NoFilter'):
                    ra_us=float(np.median([r['ns_per_query']/1000 for r in cells['RA6']]));base_us=float(np.median([r['ns_per_query']/1000 for r in cells[baseline]]));saving=base_us-ra_us
                    measured=ds in ('clark','sis');extra=None;be=None
                    if measured:
                        extra=config[ds]['RA6']['incremental_train_score_select_build_s']-(config[ds][baseline]['incremental_train_score_select_build_s'] if baseline!='NoFilter' else 0)
                        if saving>0:be=max(0.,extra)*1e6/saving
                    cost.append(dict(dataset=ds,member_fraction=p,target_backend_us=target,baseline=baseline,query_saving_us=saving,positive_steady_state_slope=saving>0,measured_incremental_startup_s=extra,stationary_projection_future_queries=be,scope='shared existing training labels, constant measured per-query slope; excludes extra label backend calls/reconfiguration; no observed long-horizon payback'))
    writecsv(ROOT/'results/latency_summary.csv',latency);writecsv(ROOT/'results/break_even.csv',cost)
    audit=json.loads((ROOT/'results/audit.json').read_text());assert audit['status']=='complete'
    out=dict(status='passed',zero_rows=len(zs),order_rows=len(cs),numeric_cases=len(nums),query_timing_windows=len(os),all_budgets_and_FN=True,zero_tree=zsummary,stage_comparison=stage,numerical=numerical,query_comparisons={ds:dict(RA_wins_BF=sum(r['query_saving_us']>0 for r in cost if r['dataset']==ds and r['baseline']=='BF'),cells=sum(r['dataset']==ds and r['baseline']=='BF' for r in cost)) for ds in DMATRIX},peak_RSS=max(w['peak_rss_bytes'] for w in raw),report_wall_s=time.perf_counter()-start)
    save(ROOT/'results/verification.json',out)
    lines=['# 第54轮：审查清单补充实验结果','','完整矩阵核验通过，详见results/verification.json。旧实验代码与论文未改，本轮没有自动发布。','',f"零树186行；重加权/同频不同序168行；6个固定分区数值参考；完整raw-query实际计时1071窗。最高worker RSS {out['peak_RSS']/1024**3:.3f}GiB。",'','## 1. Exact-key与四本账','','第53轮434行账单只读扩展见results/four_ledgers.csv；部署预算、前缀反事实索引、learning逻辑/retained内存及worker共享peak RSS分列。共享peak不能冒充方法独占构建峰值。选择时间沿用旧测量；本轮四代表性任务追加实际raw-query执行，输入和完整backend均共享。','', '## 2. t=0新变体','','| cohort / method | t=0次数 | 对BF 胜/平/负 | 平滑比中位 |','| --- | ---: | --- | ---: |']
    for cohort,mm in zsummary.items():
        for m,s in mm.items():lines.append(f"| {cohort}/{m} | {s['zero_selected']}/{s['cases']} | {s['wins']}/{s['ties']}/{s['losses']} | {s['median_smoothed_ratio']:.6f} |")
    lines+=['','t=0预测候选与learning gate是两种新变体，不混同；不承诺tail no-regret或无重复时等于Gama。旧第17/20轮存档仅作为背景，不冒充本轮。','', '## 3. 联合参考与迭代','','| 数据/KiB | 第3步epsilon残差 | 目标相对变化 | 3步过双阈值 | SA参考gap | FA参考gap |','| --- | ---: | ---: | --- | ---: | ---: |']
    for n in numerical:lines.append(f"| {n['dataset']}/{n['budget_kib']} | {n['epsilon_residual3']:.6g} | {n['objective_residual3']:.6g} | {n['pass3']} | {n['SA_reference_gap']} | {n['FA_reference_gap']} |")
    lines+=['','数值参考为固定分区可行网格＋7起点SLSQP，所有优化退出状态保留；不是全局最优证明。SA表格目标与高精度FA目标分开，不能用于声称完整DP/CLOCK耦合全局最优。effective FA T不是SA物理单一T。','', '| 对h-Replay | 胜/平/负 | 配对平滑比中位 |','| --- | --- | ---: |']
    for m,s in stage.items():lines.append(f"| {m} | {s['wins']}/{s['ties']}/{s['losses']} | {s['median_smoothed_ratio']:.6f} |")
    lines+=['','## 4. 正比例与backend成本','','[全部时延/吞吐](results/latency_summary.csv)，[回本必要条件与外推](results/break_even.csv)，每个online JSON包含校准实际服务时间、真实mask/cache核验及阶段成本。','']
    for ds,s in out['query_comparisons'].items():lines.append(f"- {ds}：RA实际query均值时延中位胜BF {s['RA_wins_BF']}/{s['cells']}个比例×backend设置。")
    lines+=['','后端是完整raw-key集合服务替身＋校准CPU延迟，不是生产DB、SQLite或远端RTT。成员key均匀重采样，负query保持原tail相对顺序，SIS99.84%也是比例匹配重采样而非原自然流。若RA慢或启动未回本均完整保留；原URL/MAWI模型复用，没有伪填训练0秒。','', '## 5. 同频不同序','','四order的learning和tail分别频数逐项相等、H相同。RA频率预测输入和最终配置逐位相同；CLOCK/learning Replay可不同。全部order、配置与FP见results/order_rows.csv；绝不把这一干预当新的真实应用。','', '## 6. 1076全案例与文字边界','','results/absolute1076.csv含index/fp64各1076case×三对照，包含低FP和绝对差；results/audit.json含8dataset与原4flow等权cluster bootstrap（20000次、seed5401）。少量cluster描述性区间不是等价检验/普遍优越性证明，也不重新划组追p<.05。','', '时间口径：selection=候选预测/构建/学习回放；construction=特征、训练、prefix打分及实体准备（旧模型复用时不声称完整构建）；end-to-end=query原key处理、推理、cache/BF、backend及反馈。49×旧选择规模实验不能替代本轮任何总时间。','', 'Eq10不填满时：冻结Population.at_capacity返回末网格mass，solve用T上界1000H处的可行epsilon，不是等式根；直接数值参考也明确同上界。GT19十四case明细仍在docs/review_evidence_20261123/gt19_14_cases.csv（两格式28行），新审计核对其来源SHA，不更改原报告。','', '报告不预设审稿决定或录用概率；性能定位应分别陈述选择成本和条件性FP收益，不使用“相当”暗示已经完成等价性统计检验。','']
    (ROOT/'README.md').write_text('\n'.join(lines));print('REPORT_VERIFIED',flush=True)

if __name__=='__main__':main()
