"""Read-only case verification followed by deterministic aggregate report generation."""
from pathlib import Path
from statistics import median
import csv
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
METHODS=('Gama','Replay','RA-global','RA-PLBF-GT19','BF+Cache')


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(p,data):p.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in freeze['sources'].items():assert sha(BLOOM/p)==h,p
    cases=[];controls=[];source_hashes={}
    for seed in (3601,3602,3603):
        p=ROOT/f'results/seed{seed}.json';d=json.loads(p.read_text());source_hashes[str(p.relative_to(ROOT))]=sha(p)
        assert d['status']=='complete' and d['freeze_sha256']==sha(ROOT/'plan/freeze.json')
        assert d['members']==32581 and d['native_threads']==1
        assert {(r['budget_kib'],r['method']) for r in d['rows']}=={(b,m) for b in (8,16,32) for m in METHODS}
        for r in d['rows']:
            assert r['member_fn']==0 and r['processed']==d['tail_queries'] and r['cutoff']==0
            assert r['total_bytes']==sum(r[k] for k in ('model_payload_bytes','bf_payload_bytes','metadata_bytes','array_header_bytes','cache_physical_bytes'))<=r['budget_kib']*1024
            cases.append(dict(seed=seed,**r))
        assert {c['budget_kib'] for c in d['controls']}=={8,16,32}
        for c in d['controls']:
            assert c['status']=='complete', 'A control is infeasible or incomplete; do not report complete 27 rows'
            assert len(c['rows'])==3 and {r['arm'] for r in c['rows']}=={'h','traffic','miss'}
            assert not c['actual_clock_fixed_T_condition']
            for r in c['rows']:
                assert r['member_fn']==r['physical']['member_fn']==0 and r['processed']==d['tail_queries'] and r['cutoff']==0
                assert r['cache_physical_bytes']==c['cache_bytes']
                assert r['physical']['used_bits']<=c['bf_budget_bits'] and r['total_bytes']<=c['budget_kib']*1024
                assert r['total_bytes']==sum(r[k] for k in ('model_payload_bytes','metadata_reserved_bytes','array_header_reserved_bytes','cache_physical_bytes'))+r['physical']['payload_bytes']
                controls.append(dict(seed=seed,budget_kib=c['budget_kib'],trees=c['trees'],partition_sha256=c['partition_sha256'],**r))
    assert len(cases)==45 and len(controls)==27
    columns=('seed','budget_kib','method','trees','cache_frac','fp','total_bytes','model_payload_bytes','bf_payload_bytes','cache_physical_bytes','build_and_select_s','tail_replay_s')
    with (ROOT/'results/main.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');w.writeheader();w.writerows({k:r[k] for k in columns} for r in cases)
    columns=('seed','budget_kib','arm','trees','fp','total_bytes','cache_physical_bytes','build_s','tail_replay_s','partition_sha256')
    with (ROOT/'results/controls.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');w.writeheader();w.writerows({k:r[k] for k in columns} for r in controls)
    def outcome(pairs):return dict(win=sum(a<b for a,b in pairs),tie=sum(a==b for a,b in pairs),loss=sum(a>b for a,b in pairs),median_smoothed_ratio=median((a+1)/(b+1) for a,b in pairs))
    comparisons={}
    for opponent in ('Gama','Replay','RA-global','BF+Cache'):
        pairs=[]
        for seed in (3601,3602,3603):
            for b in (8,16,32):
                values={r['method']:r['fp'] for r in cases if r['seed']==seed and r['budget_kib']==b}
                pairs.append((values['RA-PLBF-GT19'],values[opponent]))
        comparisons[opponent]=outcome(pairs)
    control_comparisons={}
    for opponent in ('h','traffic'):
        pairs=[]
        for seed in (3601,3602,3603):
            for b in (8,16,32):
                values={r['arm']:r['fp'] for r in controls if r['seed']==seed and r['budget_kib']==b}
                pairs.append((values['miss'],values[opponent]))
        control_comparisons[opponent]=outcome(pairs)
    text=['# Round37：ClarkNet五方法与固定配置对照','',
          '全部45条主比较＋27条固定配置消融完成。数据资格先于方法效果筛选：第36轮选出ClarkNet，Saskatchewan未过门槛未纳入。没有人工改造重复度、协议标签特征或尾段选赢家。','',
          '## 五方法：每预算3个seed的FP中位数','',
          '| KiB | Gama | Replay | RA-global | RA-PLBF-GT19 | BF+Cache | RA/BF配对平滑比中位数 |','| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for b in (8,16,32):
        vals={m:median(r['fp'] for r in cases if r['budget_kib']==b and r['method']==m) for m in METHODS}
        ratios=[]
        for seed in (3601,3602,3603):
            rr={r['method']:r['fp'] for r in cases if r['seed']==seed and r['budget_kib']==b}
            ratios.append((rr['RA-PLBF-GT19']+1)/(rr['BF+Cache']+1))
        text.append('| '+str(b)+' | '+' | '.join(str(vals[m]) for m in METHODS)+f' | {median(ratios):.6f} |')
    text += ['', '每对比值先计算(FP_RA+1)/(FP_B+1)，再取中位数，不以聚合FP之比替代。下表9个预算×seed共享同一自然日志，不是9个独立真实工作负载。', '',
             '| RA相对方法 | 胜/平/负 | 配对平滑比中位数 |','| --- | ---: | ---: |']
    for opponent,r in comparisons.items():text.append(f'| {opponent} | {r["win"]}/{r["tie"]}/{r["loss"]} | {r["median_smoothed_ratio"]:.6f} |')
    text += ['', '## 固定配置：不更换树、分区或Cache份额','',
             '固定10% cache，按validation选择anchor后锁定模型、分区与BF位预算。h、traffic和miss均用同一截断连续解和同一整数packed-BF构建器。这里不是RA6算法本身的重命名。', '',
             '| seed | KiB | trees | h FP | traffic FP | miss FP | miss/h | miss/traffic |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for seed in (3601,3602,3603):
        for b in (8,16,32):
            rows=[r for r in controls if r['seed']==seed and r['budget_kib']==b];v={r['arm']:r['fp'] for r in rows}
            text.append(f'| {seed} | {b} | {rows[0]["trees"]} | {v["h"]} | {v["traffic"]} | {v["miss"]} | {(v["miss"]+1)/(v["h"]+1):.6f} | {(v["miss"]+1)/(v["traffic"]+1):.6f} |')
    for opponent,r in control_comparisons.items():text += ['',f'miss相对{opponent}：{r["win"]}胜/{r["tie"]}平/{r["loss"]}负，配对平滑比中位数{r["median_smoothed_ratio"]:.6f}。']
    text += ['', '## 边界与资源','',
             '- 模型和Cache一起计入8/16/32KiB Filter预算，所有实体构建与最终Cache全成员检查0FN。后端完整成员hash索引8×32581＋ndarray header额外单列；不是任意后端免费自带。',
             '- 训练、评分、索引、摘要、JIT、构建/选择和尾段回放分别计时，见逐seed JSON和CSV。回放基于已计算static flags，不是完整模型计算/特征提取/远程后端的端到端延迟，不能据此宣称系统吞吐胜出。',
             '- 资格诊断16树开发AUC逐seed复现。正式选择仍使用完整原树/cache网格，未依据尾段FP选树、改预算或改数据。RA-global与RA主比较可能选不同配置，不能把差异全归给权重。',
             '- traffic单独控制请求流行度质量；miss相对h的收益不能自动归给cache-resistant部分，须同时看miss相对traffic。',
             '- 保存固定miss系数的连续目标和双内点AM/GM核验，但实体CLOCK下驻留随分配改变，不满足外生固定T，故理论因子不是实际FP收益保证。',
             '- 原始两周日志有时间回退，保持原记录顺序；冲突排除和完整成员目录为回溯构造，不能冒充动态网站前瞻部署。日志为1995年，成员32581，未解决现代或超大目录证据缺口。',
             '- 所有失败方向、零/低FP、高预算点均保留，不为显著性换分组；三seed不是独立工作负载。不改论文或旧实验。']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n')
    result=dict(status='verified',main_rows=45,control_rows=27,member_fn=0,all_budgets_pass=True,
                main_comparisons=comparisons,control_comparisons=control_comparisons,source_files=source_hashes,
                freeze_sha256=sha(ROOT/'plan/freeze.json'))
    save(ROOT/'results/verification.json',result)
    print('VERIFIED_ROUND37',json.dumps(result,ensure_ascii=False),flush=True)
    return result


if __name__=='__main__':main()
