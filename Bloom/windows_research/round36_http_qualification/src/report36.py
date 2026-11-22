"""Verify and report every qualification result, including failed gates."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fetch36 import save,sha
from diagnose36 import qualify


def report():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    bloom=ROOT.parents[1]
    for p,h in freeze['sources'].items():assert sha(bloom/p)==h,p
    receipts=json.loads((ROOT/'results/downloads.json').read_text())
    assert receipts['status']=='complete' and all(r['crc_verified'] for r in receipts['files'])
    rows=[];hashes={}
    for name in ('clarknet','sask'):
        path=ROOT/f'results/{name}.json';d=json.loads(path.read_text())
        hashes[str(path.relative_to(ROOT))]=sha(path)
        assert d['status']=='complete' and d['freeze_sha256']==sha(ROOT/'plan/freeze.json')
        assert d['qualification']==qualify(d['data'],d['diagnostics'])
        assert d['data']['retained_404_requests']+d['data']['conflicting_404_requests']==int(d['data']['status_counts'].get('404',0))
        assert d['data']['development']['requests']+d['data']['tail']['requests']==d['data']['retained_404_requests']
        for r in d['diagnostics']:
            if r['regions']:
                assert sum(g['learning_requests'] for g in r['regions'])==r['learning_requests']
                assert sum(g['learning_distinct'] for g in r['regions'])==r['learning_distinct']
                assert sum(g['members'] for g in r['regions'])==d['data']['members']
            assert r['train_negatives']+r['validation_negatives']+r['negative_pool']==d['data']['negative_keys']
        rows.append(d)
    out=['# Round36：真实HTTP轨迹资格审计','',
         '两份ClarkNet文件合并为一个工作负载；Saskatchewan为另一个。三份完整gzip均校验；本轮未构建任何BF、未测五方法FP，不能当作新增方法效果证据。',
         '', '| 工作负载 | 稳定成员 | 负key | 稳定404请求 | 404保留率 | 开发AUC中位数 | 特征重叠比例 | 学习region重复度差 | 完整对照资格 |',
         '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for d in rows:
        m=d['data'];q=d['qualification'];a=q['median_development_auc'];astr=f'{a:.4f}' if a is not None else 'NA'
        out.append(f'| {d["dataset"]} | {m["members"]} | {m["negative_keys"]} | {m["retained_404_requests"]} | {m["retained_404_fraction"]:.4f} | {astr} | {q["median_feature_overlap_fraction"]:.4f} | {q["median_region_repeat_gap"]:.4f} | {"通过" if q["eligible_for_full_comparison"] else "未通过"} |')
    for d in rows:
        m=d['data'];q=d['qualification']
        out += ['',f'## {d["dataset"]}', '',f'- 记录实际起止：{m["first_timestamp"]} → {m["last_timestamp"]}；记录顺序时间回退{m["recorded_order_time_reversals"]}次，不重新排序。',
                f'- 全部行{m["lines"]}；解析GET {m["parsed_GET"]}；跳过分类：`{json.dumps(m["skipped"],ensure_ascii=False)}`。',
                f'- 冲突key {m["conflicting_keys"]}，排除404请求{m["conflicting_404_requests"]}；开发404而首次成功在尾段的key {m["development_404_then_future_success_keys"]}；反向变化{m["development_success_then_future_404_keys"]}。',
                f'- 未过门槛：`{", ".join(q["failed_checks"]) or "无"}`。大目录门槛（>=50000成员）：{q["larger_catalog_ge_50000"]}。',
                f'- 解析/特征/写出：{m["parse_feature_and_write_s"]:.3f}s；完整本负载准备及诊断：{d["wall_s"]:.3f}s；进程累计peak RSS {d["peak_rss_bytes"]}B。',
                '', '| seed | train / validation负key | learning / tail请求 | 开发AUC | 学习重复比例 | 有支持region数 | region重复差 | train s | score s |',
                '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
        for r in d['diagnostics']:
            a=r['development_auc'];astr=f'{a:.4f}' if a is not None else 'NA'
            out.append(f'| {r["seed"]} | {r["train_negatives"]} / {r["validation_negatives"]} | {r["learning_requests"]} / {r["tail_requests"]} | {astr} | {r["learning_repeat_fraction"]:.4f} | {r["supported_regions"]} | {r["region_repeat_gap"]:.4f} | {r["training_s"]:.3f} | {r["scoring_s"]:.3f} |')
    eligible=[d['dataset'] for d in rows if d['qualification']['eligible_for_full_comparison']]
    out += ['', '## 解释边界', '',
            '- 这是回溯稳定子集：成员目录和冲突排除使用完整日志，**不是动态网站前瞻部署**。长跨度中排除的冲突和被保留的404比例必须共同阅读。',
            '- 使用真实HTTP status，不把cache miss、0 bytes或HTTP协议版本当正负标签。输入特征不包含status、响应大小、客户身份、时间或频率。',
            '- region为固定16树的开发验证负分数分位区间，不是正式Gama/PLBF分区；重复度只取学习段。区域差异不能单独证明Prop5.3条件或收益。',
            '- 三seed共享日志，不能当三个独立真实工作负载。AUC和词法特征重叠不能直接证明模型比BF更划算。',
            '- 两份均为1995年日志；通过规模门槛也不能称为现代。筛查门槛是事前工程决策，不是模型效果定理。未通过不等于该方法在此数据上无用。',
            '- 未用RA胜负筛数据。通过者仍需独立冻结五方法同预算对照和固定配置权重消融；没有通过者则如实保留，不降低门槛。',
            '- 不发布原始日志、客户身份、request targets或逐key数组；本轮只写实验及MD，不修改论文。',
            '', f'进入后续完整对照的候选：{", ".join(eligible) or "无"}。该资格结论不是方法效果结论。']
    (ROOT/'results/report.md').write_text('\n'.join(out)+'\n')
    result=dict(status='verified',workloads=2,diagnostic_rows=6,eligible=eligible,filter_effects_measured=False,
                source_files=hashes,freeze_sha256=sha(ROOT/'plan/freeze.json'))
    save(ROOT/'results/verification.json',result)
    print('REPORT_VERIFIED',json.dumps(result,ensure_ascii=False),flush=True)
    return result


if __name__=='__main__':report()
