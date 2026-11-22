"""Deterministic verification and summaries; all prespecified H rules and cohorts retained."""
from pathlib import Path
from statistics import median
import csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
RULES=('quarter','matched','fourfold','three_learning')
COHORTS=('paper_zipf','real_trace','tcp_only','http')


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def summarize(rows):
    ratios=[r['fp_ratio_to_matched'] for r in rows]
    return dict(cases=len(rows),wins=sum(r<1 for r in ratios),ties=sum(r==1 for r in ratios),losses=sum(r>1 for r in ratios),
                median_ratio=median(ratios),min_ratio=min(ratios),max_ratio=max(ratios),
                configurations_changed=sum(not r['same_configuration_as_matched'] for r in rows),
                payloads_changed=sum(not r['payload_byte_equal_matched'] for r in rows),
                top5_changed=sum(r['top5_overlap']<5 for r in rows),
                median_select_build_s=median(r['select_build_s'] for r in rows))


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in freeze['sources'].items():assert sha(BLOOM/p)==h,p
    rows=[];sources={};matches=0;new_matches=0;fn_total=0;counts={'index':0,'fp64':0}
    for job in freeze['jobs']:
        ds,seed,mode=job['dataset'],job['seed'],job['cache'];path=ROOT/f'results/{ds}_{seed}_{mode}.json'
        d=json.loads(path.read_text());sources[str(path.relative_to(ROOT))]=sha(path)
        assert d['status']=='complete' and d['freeze_sha256']==sha(ROOT/'plan/freeze.json') and d['native_threads']==1
        if mode=='fp64':
            assert not d['retains_sorted_member_index'] and d['backend_index_payload_bytes']==d['backend_index_physical_bytes']==0
        else:assert d['retains_sorted_member_index'] and d['backend_index_payload_bytes']==8*d['members']
        expected=[c for c in freeze['cases'] if c['dataset']==ds and c['seed']==seed]
        assert {c['budget_kib'] for c in d['cases']}=={c['budget_kib'] for c in expected}
        for c in d['cases']:
            assert set(c['rows'])==set(RULES)
            matched=c['rows']['matched'];assert matched['assumed_H']==d['actual_H']
            if c['reference_verification'].startswith('new fp64'):new_matches+=1
            else:assert 'reproduced' in c['reference_verification'];matches+=1
            expected_H=dict(quarter=max(1,d['actual_H']//4),matched=d['actual_H'],fourfold=4*d['actual_H'],three_learning=3*d['learning_queries'])
            for rule in RULES:
                r=c['rows'][rule];info=r['selection_info']
                assert r['assumed_H']==expected_H[rule] and r['actual_H']==d['actual_H']
                assert r['processed']==d['actual_H'] and r['cutoff']==0
                assert info['stage1_H']==[r['assumed_H']] and len(info['stage2_H'])==info['built']
                assert all(h==r['assumed_H'] for h in info['stage2_H'])
                assert len(info['table'])==info['candidates'] and info['built']==min(5,len(info['table']))
                assert r['total_bytes']==sum(r[k] for k in ('model_payload_bytes','metadata_bytes','array_header_bytes','bf_payload_bytes','cache_bytes'))<=c['budget_kib']*1024
                assert r['payload']['member_fn']==0
                if mode=='index':assert r['member_cache_hits_final']==0
                else:assert r['fp64_ideal_hash_bound_per_query']==min(1.,r['slots']/2**64)
                if r['assumed_H']==matched['assumed_H']:
                    assert r['payload_byte_equal_matched'] and r['cache_byte_equal_matched'] and r['fp']==matched['fp']
                assert r['fp_ratio_to_matched']==(r['fp']+1)/(matched['fp']+1)
                row={k:r[k] for k in ('assumed_H','actual_H','assumed_over_actual','actual_over_assumed','trees','frac','cache_bytes','slots','total_bytes','fp',
                     'member_cache_hits_final','fp64_ideal_hash_bound_per_query','payload_check_s','tail_replay_s','member_cache_check_s',
                     'same_configuration_as_matched','payload_byte_equal_matched','cache_byte_equal_matched','fp_ratio_to_matched','rank_positions_changed','top5_overlap')}
                row.update(dataset=ds,seed=seed,cache=mode,budget_kib=c['budget_kib'],cohort=c['cohort'],rule=rule,
                           learning_queries=d['learning_queries'],matched_fp=matched['fp'],select_build_s=info['select_build_wall_s'],candidate_diagnostic_s=info['candidate_diagnostic_s'])
                rows.append(row);fn_total+=r['member_cache_hits_final'];counts[mode]+=1
    assert len(rows)==168 and counts=={'index':84,'fp64':84} and matches==33 and new_matches==9
    with (ROOT/'results/rows.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    aggregate={};groups={}
    for mode in ('index','fp64'):
        for rule in RULES:
            aggregate[f'{mode}/{rule}']=summarize([r for r in rows if r['cache']==mode and r['rule']==rule])
            for cohort in COHORTS:
                groups[f'{mode}/{rule}/{cohort}']=summarize([r for r in rows if r['cache']==mode and r['rule']==rule and r['cohort']==cohort])
    text=['# Round38：预测H误设敏感性','',
          '21个固定case keys ×2种cache格式 ×4种预测规则 =168条选择/评估。学习流、真实尾段、预算、模型规则和成员集合固定，只改变两阶段接收的预测H。未截断、复制或延长实际尾段。', '',
          '33个matched参照复现（旧12例×两格式24行＋ClarkNet-index9行）；ClarkNet-fp64的9个matched配置为新补充，不是留出前证据。','',
          '| 格式 | 预测规则 | 案例 | FP较matched胜/平/负 | 平滑FP比中位数 | 最小/最大比 | 配置变化 | payload变化 | top5变化 |',
          '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for mode in ('index','fp64'):
        for rule in RULES:
            r=aggregate[f'{mode}/{rule}']
            text.append(f'| {mode} | {rule} | {r["cases"]} | {r["wins"]}/{r["ties"]}/{r["losses"]} | {r["median_ratio"]:.6f} | {r["min_ratio"]:.6f}/{r["max_ratio"]:.6f} | {r["configurations_changed"]} | {r["payloads_changed"]} | {r["top5_changed"]} |')
    text += ['', 'quarter=floor(H_actual/4)且至少1；fourfold=4×H_actual；matched为正确长度参照；three_learning=3×已观察学习请求数。表中比值先逐case计算(FP_rule+1)/(FP_matched+1)，再聚合，不能说成未经平滑的总FP降幅。', '',
             '## 全部非matched案例（包括无变化）','',
             '| 数据/seed | KiB | 格式 | 规则 | 预测/实际H | matched FP | 实际FP | 平滑比 |',
             '| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |']
    for r in rows:
        if r['rule']=='matched':continue
        text.append(f'| {r["dataset"]}/{r["seed"]} | {r["budget_kib"]} | {r["cache"]} | {r["rule"]} | {r["assumed_over_actual"]:.6f} | {r["matched_fp"]} | {r["fp"]} | {r["fp_ratio_to_matched"]:.6f} |')
    text += ['', '## 解释与边界','',
             '- 所有选择调用的API均不接受tail数组；H观察器逐次核对stage1和每个stage2调用的H一致，不重算候选表、不改返回对象/排序。',
             '- 相同整数H的重复规则须真实逐字节匹配模型、分区、位图、flags和最终cache；与matched相同payload的案例也须FP与cache状态一致。配置不变并不自动意味着位图不变。',
             '- 全部实体BF构建的有限成员检查0FN、预算通过。最终cache成员命中总数为'+str(fn_total)+'；index要求为0，fp64仅记录有限集合观测，仍有理想非对抗hash假设下的单query界，不是普适或生命周期零FN。',
             '- fp64 worker不构建或持有排序成员索引，不计算safe prefix；构建/验证所需成员hash数组仍在harness中。index的8*n+header额外资源单列，不能说成通用后端免费提供。',
             '- 四规则按case循环移位运行，加载、模型/评分、索引、GT摘要、JIT、选择/构建、候选记录、payload复建和评估/成员检查分别计时。单次wall计时和共享日志的seed不是独立时延重复。',
             '- 原论文数据、原真实流、TCP-only、HTTP四类汇总均保留在summary.json，不更换统计分组追求显著性。H误设偶然比matched好不能用来事后选H。',
             '- H可作为计划性复核/重建前的预计negative请求数；3L为只依赖已观察数据的预设启发式，不承诺最优。本轮不是开放流重建/漂移适应实验，也不证明无限期运行保证。',
             '- ClarkNet沿用回溯稳定子集与1995年日志；不新增现代/前瞻部署证据。没有使用MAWI24重新选H，也未改变旧留出记录。',
             '- 旧E10学习比例敏感性与本轮不同：它总是给出实际尾段长度，本轮隔离预测输入误设。代码和结果另轮归档，论文未改。']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n')
    save(ROOT/'results/summary.json',dict(overall=aggregate,by_cohort=groups))
    result=dict(status='verified',case_keys=21,cache_formats=2,rules=4,rows=168,archived_matched_reproduced=matches,new_http_fp64_matched=new_matches,
                final_member_cache_hits_total=fn_total,source_files=sources,freeze_sha256=sha(ROOT/'plan/freeze.json'))
    save(ROOT/'results/verification.json',result)
    print('VERIFIED_ROUND38',json.dumps(result,ensure_ascii=False),flush=True)
    return result


if __name__=='__main__':main()
