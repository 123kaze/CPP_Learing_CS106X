"""Durability evidence and actual-space reference; no latency/net-ROI claim."""
import csv,json
from learned_engine_run import ROOT,sha
OUT=ROOT/'results/learned-policy'
CONTROL=ROOT/'results/budget-ribbon'
def main():
    assert json.loads((OUT/'complete.json').read_text())['returncode']==0
    assert json.loads((CONTROL/'complete.json').read_text())['returncode']==0
    cases=json.loads((OUT/'rows.json').read_text())
    cases += [dict(method='budget-ribbon',stage=r['stage'],records=r['records']) for r in json.loads((CONTROL/'rows.json').read_text())]
    flat=[]
    for case in cases:
        got=case['records'];p=next(r for r in got if r['kind']=='policy_stats');assert next(r for r in got if r['kind']=='member_check')['wrong']==0
        for q in [r for r in got if r['kind']=='query']:
            flat.append(dict(method=case['method'],stage=case['stage'],population=q['population'],queries=q['queries'],wrong=q['wrong'],false_file_hits=q['bloom_full_positive']-q['bloom_full_true_positive'],true_file_hits=q['bloom_full_true_positive'],block_read_count=q['block_read_count'],filter_payload_bytes=p['live_filter_serialized_bytes'],model_payload_bytes=p['resident_model_payload_bytes'],filter_plus_model_bytes=p['filter_plus_model_payload_bytes'],model_calls=q['model_evaluations'],model_reuses=q['model_reuses'],direct_accepts=q['direct_accepts'],bf_probes=q['bf_probes'],failopen_calls=q['failopen_calls'],cpu_seconds=q['cpu_seconds'],wall_seconds=q['wall_seconds'],peak_rss_bytes=p['peak_rss_bytes'],build_model_calls=p['build_model_evaluations'],peak_hash_capacity_bytes=p['peak_hash_vector_capacity_bytes']))
    with (OUT/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    def get(method,stage,pop):return next(r for r in flat if r['method']==method and r['stage']==stage and r['population']==pop)
    a=get('learned','final','negative');b=get('budget-ribbon','final','negative');assert a['direct_accepts']==160>b['false_file_hits']==113
    lines=['# 真实RocksDB learned policy：持久化通过，当前优势被强Ribbon否定','',
        '2026-10-26。已实现固定key-only模型的真实FilterPolicy。功能门槛通过，尚未形成新算法或净收益贡献。','',
        '## 实际完成','',
        '基于官方8.9.1内部FilterBits接口，SST保存64B模式/模型ID/cut/k/长度/校验头与BF；模型1独立保存到DB旁并核对hash。全部模型拒绝成员实际插入backup，不随机抽样。一次Get内按key和模型ID复用score。异常/缺失模型保守放行并计数。','',
        '四种policy在新DB中执行build、fresh-process reopen、manual compaction、fresh final reopen；learned还实际移走模型文件只读重开，恢复后再重开。18个引擎进程和1个单元进程全退出0，另补4个空间额度控制进程。22阶段的176万次完整成员/值检查和88万次query结果均正确。fixture已经使用过，不冒称新的独立确认。','',
        '## 为什么补空间控制','',
        '标准RibbonPolicy(8,0)在flush选BF，compaction后实际只用56974B，而learned约79968B。仅比较同一个8bpk参数，会给Ribbon留约23KB未用空间。补充控制在flush用BF7.9，compaction输出用Ribbon11.0；11.0只依据空间换算事先固定，没有依据query误报调参。最终实际76558B，各阶段均≤80000B。这是已有public API委托机制，不是新算法。','',
        '## 实际文件误命中','',
        '每行各20000个negative/positive fixture。reopen为4个重叠L0文件，final为compaction后6个L6范围文件；positive栏不含必需的20000次真实命中。','',
        '| policy | 状态 | 过滤器+模型载荷 B | negative误文件命中 | positive额外误文件命中 |',
        '|---|---|---:|---:|---:|']
    for method in ('bloom','packed','learned','ribbon','budget-ribbon'):
        for state in ('reopen','final'):
            n=get(method,state,'negative');p=get(method,state,'positive')
            lines.append(f'| {method} | {state} | {n["filter_plus_model_bytes"]} | {n["false_file_hits"]} | {p["false_file_hits"]} |')
    lines += ['',
        'packed与learned使用同一packed BF/hash内核；bloom/ribbon为engine的8bpk/8等效bpk，budget-ribbon为补充空间控制。两个原始8bpk配置实际稍超80000B，保留其真实数值，不称完全相同空间。','',
        '## 当前固定配置为什么不应继续优化','',
        'compaction后learned误命中250次，空间控制Ribbon仅113次，且空间76558B低于79968B。learned的250次中，160次是模型直接放行，backup只贡献90次。','',
        '对这个固定模型/cut/冻结query轨迹，哪怕backup完美，160次直接放行仍无法消除，已经超过Ribbon的113次。故继续加速backup/迁移或调BF哈希，不能让这个固定cut在negative误文件命中数量上胜出。它不排除其他模型、阈值、PLBF/CLBF，也不是未来FPR保证或新定理。','',
        '4个L0文件时，learned相对空间控制将negative误命中1977→1100，却将positive额外误命中740→8802。仅比较同价错误访问数，positive比例超过877/(877+8062)≈9.81%就失去优势，尚未计模型推理。不能只展示全局negative FPR下降。','',
        '## 正确性和复用','',
        '正常learned阶段没有invalid reader或fail-open。20000negative在4个L0文件上产生80000次filter调用，只算20000次模型，复用60000次；positive复用30000次。范围文件阶段基本每次只查一个filter，复用机会消失。','',
        'missing-model阶段全部成员/值仍正确，但触发120000次保守放行；这是退化费用，不是免费容错。恢复模型后计数回到正常。正确性条件和推导见[learned-policy-proof.md](learned-policy-proof.md)，当前没有一般新旧模型并发切换或crash保证。','',
        '## 费用与内存边界','',
        f'正常packed/learned snapshot的持久化filter+模型载荷≤80000B，模型对象另48B。22阶段最大RSS为{max(r["peak_rss_bytes"] for r in flat)}B，8MiB只是cache配置。自定义hash向量capacity峰值packed524288B、learned262144B，未覆盖重分配瞬间、输出buffer及全部engine临时状态；内置BF/Ribbon没有这个自定义tracker，不能把其0值当零临时内存。当前没有严格resident RAM或迁移峰值预算证明。',
        'learned每次完整重建仍有80000次key特征/score计算；模型训练本轮未重做。所有compaction和queryCPU/wall留在日志。custom policy还有额外诊断计数/作用域开销，执行只有一个方法顺序、各表布局/cache不同、WSL挂载目录OS cache未知，所以这些点值不构成稳定速度排名或净收益结论。','',
        '## 下一步','',
        '停止优化当前4树/固定cut经典LBF执行器。若继续LSM主线，应先以验证数据寻找文件条件PLBF/CLBF等更强配置，保留同额度Ribbon；只有存在余量，才开发共享模型准入/全局分配。旧模型驻留、只改compaction输出、严格峰值及新颖性仍未解决。','',
        '代码：learned_policy.hpp、learned_engine.cpp/run.py/analyze.py；budget_ribbon_run.py生成公开API控制。results/learned-policy与results/budget-ribbon保存逐进程命令/退出码/日志/源hash/model-registry。控制驱动第一次因编译目录与build阶段重名退出1，未启动DB；failed-driver.py/failed-sources.json与恢复记录保留，修复只改运行目录，未调kernel或参数。','']
    (ROOT/'learned-policy-report.md').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'analysis-verification.json').write_text(json.dumps(dict(returncode=0,stages=22,rows=len(flat),source_sha256=sha(OUT/'rows.json'),control_sha256=sha(CONTROL/'rows.json'),fixedcut_direct_floor=160,budget_ribbon_false_hits=113,no_netROI_or_novelty_claim=True),indent=2))
    print('Report generated: fixedcut direct-accept floor160 > budgetRibbon113')
if __name__=='__main__':main()
