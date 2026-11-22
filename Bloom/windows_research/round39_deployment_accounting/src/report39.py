"""Verify counterfactual call accounting without presenting projections as measurements."""
from pathlib import Path
import csv,hashlib,json,sys
from statistics import median
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from account39 import calls,project,required_index_bytes,SCENARIOS
COMPARISONS=('ready_plain','ready_fixed10','shared_labels_selected_cache')


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def write_csv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in freeze['sources'].items():assert sha(BLOOM/p)==h,p
    rows=[];scenarios=[];resources=[];memory={};hashes={};case_count=0
    provenance=dict(archived_plain=0,new_plain=0,new_warm_fixed10=0,archived_selected=0,new_selected=0)
    for job in freeze['jobs']:
        ds,seed,mode=job['dataset'],job['seed'],job['cache'];p=ROOT/f'results/{ds}_{seed}_{mode}.json';d=json.loads(p.read_text())
        assert d['status']=='complete' and d['freeze_sha256']==sha(ROOT/'plan/freeze.json')
        hashes[str(p.relative_to(ROOT))]=sha(p)
        if mode=='fp64':assert not d['retains_sorted_member_index'] and d['actual_sorted_index_payload_bytes']==0
        assert d['finite_fingerprints_disjoint']
        L,H=d['learning_queries'],d['tail_queries'];mem=d['learning_state_memory'];D=mem['distinct_learning_keys']
        assert mem['retained_trace_payload_bytes']==8*L and mem['counts_only_payload_bytes']==16*D and mem['keys_counts_rates_payload_bytes']==24*D
        key=(ds,seed)
        if key in memory:assert memory[key]['counts_only_payload_bytes']==mem['counts_only_payload_bytes'] and memory[key]['retained_trace_payload_bytes']==mem['retained_trace_payload_bytes']
        else:memory[key]=dict(dataset=ds,seed=seed,**{k:v for k,v in mem.items() if k!='arrays_own_data'})
        expected=[r for r in freeze['cases'] if r['dataset']==ds and r['seed']==seed]
        assert {c['budget_kib'] for c in d['cases']}=={c['budget_kib'] for c in expected}
        for c in d['cases']:
            case_count+=1;kib=c['budget_kib'];plain=c['baselines']['plain'];fixed=c['baselines']['fixed10'];selected=c['selected_cold_baseline']
            provenance['archived_plain' if plain['provenance'].startswith('archived') else 'new_plain']+=1
            provenance['new_warm_fixed10']+=1
            provenance['archived_selected' if selected['provenance'].startswith('archived') else 'new_selected']+=1
            assert fixed['frac']==.1 and fixed['tail_start_cache_sha256']==fixed['learning_counts']['cache_sha256']
            assert fixed['learning_counts']['processed']==L and fixed['tail_counts']['processed']==H
            assert fixed['learning_counts']['member_cache_hits']==fixed['tail_counts']['member_cache_hits']==0
            assert set(r['comparison'] for r in c['comparisons'])==set(COMPARISONS)
            rr=dict(RA=c['RA_resources'],ready_plain=plain['resources'],ready_fixed10=fixed['resources'],selected_cold=selected['resources'])
            for method,r in rr.items():
                required=required_index_bytes(mode,r['cache_bytes'],d['members'],d['array_header_bytes'])
                assert r['required_index_if_absent_bytes']==required and r['additional_index_if_already_available_bytes']==0
                assert r['filter_plus_required_index_bytes']==r['filter_actual_bytes']+required and r['filter_actual_bytes']<=kib*1024
                resources.append(dict(dataset=ds,seed=seed,cache=mode,budget_kib=kib,method=method,members=d['members'],**r))
            for r in c['comparisons']:
                shared=r['comparison']=='shared_labels_selected_cache'
                baseline=selected if shared else (plain if r['comparison']=='ready_plain' else fixed)
                learn_calls=L if shared else baseline['learning_fp']
                assert r['baseline_learning_backend_calls']==learn_calls and r['baseline_tail_backend_calls']==baseline['tail_fp'] and r['ra_tail_backend_calls']==c['RA_matched_fp']
                recalculated=calls(L,H,learn_calls,baseline['tail_fp'],c['RA_matched_fp'],shared)
                for k,v in recalculated.items():assert r[k]==v,(ds,kib,mode,k)
                assert r['net_backend_calls_saved_after_one_window']==learn_calls+baseline['tail_fp']-L-c['RA_matched_fp']
                base=dict(dataset=ds,seed=seed,cache=mode,budget_kib=kib,cohort=c['cohort'],comparison=r['comparison'],learning_queries=L,tail_queries=H)
                rows.append(dict(**base,baseline_learning_backend_calls=learn_calls,baseline_tail_backend_calls=baseline['tail_fp'],ra_tail_backend_calls=c['RA_matched_fp'],**recalculated))
                assert [x['name'] for x in r['scenarios']]==[x['name'] for x in SCENARIOS]
                for scenario,params in zip(r['scenarios'],SCENARIOS):
                    recomputed=project(recalculated,**{k:v for k,v in params.items() if k!='name'})
                    assert scenario==dict(**params,**recomputed)
                    scenarios.append(dict(**base,**scenario))
    assert case_count==42 and len(rows)==126 and len(resources)==168 and len(scenarios)==756 and len(memory)==15
    assert provenance==dict(archived_plain=24,new_plain=18,new_warm_fixed10=42,archived_selected=24,new_selected=18)
    write_csv(ROOT/'results/call_accounting.csv',rows);write_csv(ROOT/'results/scenario_projections.csv',scenarios)
    write_csv(ROOT/'results/resources.csv',resources);write_csv(ROOT/'results/learning_state.csv',list(memory.values()))
    summary={}
    for mode in ('index','fp64'):
        for comparison in COMPARISONS:
            rr=[r for r in rows if r['cache']==mode and r['comparison']==comparison]
            summary[f'{mode}/{comparison}']=dict(cases=len(rr),tail_savings_positive=sum(r['tail_backend_calls_saved']>0 for r in rr),
                whole_observed_window_net_savings_positive=sum(r['net_backend_calls_saved_after_one_window']>0 for r in rr),
                whole_observed_window_net_savings_zero=sum(r['net_backend_calls_saved_after_one_window']==0 for r in rr),
                median_extra_learning_fraction=median(r['extra_learning_backend_calls']/r['learning_queries'] for r in rr),
                median_backend_only_negative_queries_over_observed_H=median(r['backend_only_break_even_negative_queries']/r['tail_queries'] for r in rr if r['backend_only_break_even_negative_queries'] is not None) if any(r['backend_only_break_even_negative_queries'] is not None for r in rr) else None)
    text=['# Round39：学习期增量成本与有条件回本','',
          '本轮是计数回放、资源核算及参数化外推，不是新的SQL/远程服务完整计时。复用第38轮42个matched-H设置，不取误设H中更好的配置。', '',
          '## 正确的学习成本差分', '',
          '`ΔL = L_negative - 已部署baseline在学习段的negative后端调用数`。不能把所有学习查询或所有成员访问都算作RA额外代价。成员访问在本批无FN、相同成员集合条件下两边抵消。', '',
          '| 格式 | 比较 | 设置数 | 尾段调用减少 | 学习＋当前尾段净调用减少 | 净调用持平 | 学习额外调用/L中位数 |',
          '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for mode in ('index','fp64'):
        for name in COMPARISONS:
            s=summary[f'{mode}/{name}']
            text.append(f'| {mode} | {name} | {s["cases"]} | {s["tail_savings_positive"]} | {s["whole_observed_window_net_savings_positive"]} | {s["whole_observed_window_net_savings_zero"]} | {s["median_extra_learning_fraction"]:.6f} |')
    text += ['', 'ready_plain：学习前已可部署的Plain BF。ready_fixed10：事前固定10% Cache，学习后保持原cache状态进入尾段；不是看当前学习数据选出的份额。shared_labels_selected_cache：两者共享同一次标签采集，再同时冷部署，增量采集为0。历史标签已经存在时增量同样为0，但不等于所有日志都完整/免费。', '',
             'shared标签行的baseline_learning_backend_calls=L表示共同新在线采集版本；若是已有历史日志，两边新增采集调用均为0，差分仍相同。其他行比较的是“强制全查询后端的新学习者”与现成baseline，不宣称这是唯一可行的在线采集协议。', '',
             '## 参数化回本，不补造缺测成本', '',
             '`ΔT(N) = A + ΔL*C/1e6 + N*[d-(1-p)*s*C]/1e6`。A为额外非lookup启动/学习处理/训练/索引/重配置净成本（本轮示例A>=0）；C为基本backend调用成本；d为每总查询额外非lookup处理成本，含模型/特征/cache与按需prefix验证差额；p为成员比例；s为当前窗口每negative query节省的调用数。', '',
             '只有`(1-p)*s*C-d>0`才有持续收益斜率。否则在非负启动/采集成本下，增大N不会使原本落后的方案自动回本。示例参数见冻结协议及scenario_projections.csv，A/C/d/p均是假设，不是新的实测生产参数；零/负收益全部保留。若周期性重新采集/重建，A与ΔL必须按周期重复计费，不能假定一次启动可供无限期摊销。', '',
             'backend-call-only的投影忽略新增CPU/启动成本，且假设未来保持观测节省率；它是有条件的理想化参照，不是实际未来最少请求数保证。A=d=0时，学习额外访问与尾段节省同时乘C，单纯提高backend单次成本不会改变按调用数计算的回本窗口。', '',
             '## 资源与正确性', '',
             '- resources.csv逐设置列RA、Plain BF、固定10% BF+Cache、学习选择BF+Cache的Filter实占、缺少索引时的辅助索引字节以及二者之和。这个和仍不包括backend数据、OS缓存、输入矩阵或全部RSS。',
             '- index且cache非空时需8*n+array header；Plain BF和fp64不需要该验证索引。若后端已有完整兼容索引，新增字节为0，但索引本身并未消失；原始key有序不意味着hash有序。',
             '- prefix验证必须在实际absent确认后执行，索引必须完整且与成员快照一致。第35轮实际SQL/TCP测过这一流程；本轮使用已确认标签和预计算safe prefixes，只计调用，不把批量预计算时间当逐miss线上开销。',
             '- 静态集合、模型、预处理和路由版本要一致。成员插入或模型/路由改变可能使旧prefix/BF失效，必须协调cache失效及必要重建，不能沿用旧零FN保证。',
             '- 本批member/negative fingerprint集合不相交，cache成员检查0命中。一般键域下fp64仍可能碰撞；严格zero-FN需求且无验证索引时，不能把fp64直接当等价替代，可选择Plain BF，或另行实现并完整计费的精确key cache。后者未在本轮实现。', '',
             '## 学习状态不保证比原始流小', '',
             'learning_state.csv按15个dataset/seed列L和D，不把多个预算与两种格式重复当成独立负载。GT19的state_bytes仅计keys+counts=16D；另有rates=8D，三数组payload为24D。与8L原始轨迹payload相比，分别在D/L>1/2、D/L>1/3时更大。这不是含header、Population中间量或RSS的完整峰值模型。',
             f'本批15个输入中，16D大于8L的有{sum(r["counts_only_payload_bytes"]>r["retained_trace_payload_bytes"] for r in memory.values())}个，24D大于8L的有{sum(r["keys_counts_rates_payload_bytes"]>r["retained_trace_payload_bytes"] for r in memory.values())}个。全distinct人工单测验证了2×/3×payload反例。', '',
             '## 可以缓解但尚未实现的采集协议', '',
             '若已有严格zero-FN且与当前快照一致的filter，拒绝本身可证明negative，只对放行请求查backend，就有可能在不增加backend调用的前提下取得全入口标签。完整入口日志/计数CPU与内存仍需支付；只取backend日志会漏掉被filter挡住的请求。fp64 cache命中不能单独当严格negative证书。这里是明确的条件性设计建议，不追认旧实验已经用了这种采集方式。', '',
             '## 可追溯性与未解决项', '',
             f'本轮新做42个学习到尾段连续cache控制、18个ClarkNet纯BF计数和18个ClarkNet学习选cache结果；24个legacy Plain BF与24个legacy学习选cache行复用已核验档案。没有把它们标成全部新执行。',
             '- 168资源行、126差分比较、756显式参数外推均保留。新ClarkNet-index BF+Cache须复现第37轮；fp64是新增补充。',
             '- 这不是第三方独立复现、不是现代KV轨迹、不是动态成员部署，也不证明完整选择器全局最优或固定点收敛。没有修改论文或冻结旧实验。']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n')
    save(ROOT/'results/summary.json',summary)
    verification=dict(status='verified',settings=42,comparisons=126,scenario_projections=756,resource_rows=168,distinct_learning_inputs=15,
        provenance=provenance,source_files=hashes,freeze_sha256=sha(ROOT/'plan/freeze.json'),scope='count_replays_and_conditional_projections_not_end_to_end_measurements')
    save(ROOT/'results/verification.json',verification);print('VERIFIED_ACCOUNT39',json.dumps(verification,ensure_ascii=False),flush=True)
    return verification


if __name__=='__main__':main()
