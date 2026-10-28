"""Build the Chinese supplement report from completed v2 result JSON files only.

No experiment execution, model loading, score calculation or holdout inspection.
V1 diagnostic runs are deliberately excluded from every quantitative table.
"""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from pathlib import Path
import statistics as S
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
MODEL = '误报流模型'
GRID = 'Gama+缓存学习期网格'
TODS = 'TODS式比例学习期网格'
GAMA = 'Gama无缓存'
METHODS = (MODEL, GRID, TODS, GAMA)
EXPECTED_DATASETS = ('cod', 'caida', 'caida_flow', 'mawi2021_flow')
EXPECTED_BACKENDS = ('clock', 'global_lru')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def write_csv(path, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt(x, digits=3):
    if x is None:
        return '—'
    return f'{x:,.{digits}f}'


def median(values):
    values=[v for v in values if v is not None]
    return float(S.median(values)) if values else None


def summarize():
    raw, costs, status, sources = [], [], [], []
    for ds in EXPECTED_DATASETS:
        for backend in EXPECTED_BACKENDS:
            folder = RESULTS / f'rerun_v2_{ds}_{backend}'
            meta_path = folder / 'run_meta.json'
            complete = meta_path.exists() and bool(read(meta_path).get('completed'))
            row_path = folder / 'rows.json'
            nrows = len(read(row_path)) if row_path.exists() else 0
            status.append(dict(dataset=ds, backend=backend, completed=complete, rows=nrows))
            if not complete:
                continue
            part = read(row_path)
            meta = read(meta_path)
            assert nrows == meta['rows']
            assert all(r['dataset'] == ds and r['backend'] == backend for r in part)
            assert all(r['member_false_negatives'] == 0 for r in part)
            assert all(r['actual_filter_state_bytes'] <= r['budget_kib'] * 1024 for r in part)
            raw.extend(part)
            costs.extend(dict(c, backend=backend) for c in read(folder / 'selection_costs.json'))
            sources.append(str(row_path.relative_to(ROOT)))
    groups = defaultdict(list)
    for r in raw:
        groups[tuple(r[k] for k in ('dataset','budget_kib','backend','workload','method'))].append(r)
    aggregates = []
    for key, rows in sorted(groups.items()):
        assert len({r['seed'] for r in rows}) == len(rows), f'Duplicate rows {key}'
        rr = dict(zip(('dataset','budget_kib','backend','workload','method'),key))
        rr.update(seeds=len(rows), fp_mean=S.mean(r['fp_tail'] for r in rows),
                  fp_std=S.stdev(r['fp_tail'] for r in rows) if len(rows)>1 else None,
                  fpr_mean=S.mean(r['fpr'] for r in rows),
                  fpr_std=S.stdev(r['fpr'] for r in rows) if len(rows)>1 else None,
                  fp_per_million=S.mean(r['fpr'] for r in rows)*1e6,
                  evaluation_queries=rows[0]['evaluation_queries'],
                  selected_configs=';'.join(f"seed{r['seed']}:t{r['trees']}/r{r['frac']}" for r in rows))
        aggregates.append(rr)
    work = defaultdict(dict)
    for r in aggregates:
        work[tuple(r[k] for k in ('dataset','budget_kib','backend','workload'))][r['method']] = r
    comparisons = []
    for key, methods in sorted(work.items()):
        expected=set(METHODS)-({TODS} if key[0]=='mawi2021_flow' and key[1]==40 else set())
        assert set(methods) == expected, f'Missing method {key}'
        row = dict(zip(('dataset','budget_kib','backend','workload'),key))
        row.update(model_grid_ratio=(methods[MODEL]['fp_mean']+1)/(methods[GRID]['fp_mean']+1),
                   model_gama_ratio=(methods[MODEL]['fp_mean']+1)/(methods[GAMA]['fp_mean']+1),
                   model_minus_grid_fp_per_million=methods[MODEL]['fp_per_million']-methods[GRID]['fp_per_million'],
                   model_minus_gama_fp_per_million=methods[MODEL]['fp_per_million']-methods[GAMA]['fp_per_million'])
        for short,m in [('model',MODEL),('grid',GRID),('tods',TODS),('gama',GAMA)]:
            for field in ('fp_mean','fp_std','fpr_mean','fpr_std','fp_per_million','seeds'):
                row[f'{short}_{field}'] = methods.get(m,{}).get(field)
        comparisons.append(row)
    settings = defaultdict(list)
    for row in comparisons:
        settings[tuple(row[k] for k in ('dataset','budget_kib','backend'))].append(row)
    setting_summary = []
    for key, rows in sorted(settings.items()):
        ratios = [r['model_grid_ratio'] for r in rows]
        gama_ratios = [r['model_gama_ratio'] for r in rows]
        setting_summary.append(dict(zip(('dataset','budget_kib','backend'),key)) | dict(
            workloads=len(rows), model_grid_ratio_median=median(ratios),model_grid_ratio_worst=max(ratios),
            model_gama_ratio_median=median(gama_ratios),model_gama_ratio_worst=max(gama_ratios),
            model_beats_grid=sum(r < 1-1e-12 for r in ratios),model_ties_grid=sum(abs(r-1)<=1e-12 for r in ratios),
            model_loses_grid=sum(r > 1+1e-12 for r in ratios),
            worst_grid_workload=max(rows,key=lambda r:r['model_grid_ratio'])['workload']))
    cost_groups = defaultdict(list)
    for row in costs:
        cost_groups[tuple(row[k] for k in ('dataset','budget_kib','backend'))].append(row)
    efficiency = []
    for key, rows in sorted(cost_groups.items()):
        med_model = median([r['model_selection_seconds'] for r in rows])
        med_grid = median([r['grid_selection_seconds'] for r in rows])
        matching = [r for r in raw if tuple(r[k] for k in ('dataset','budget_kib','backend')) == key]
        efficiency.append(dict(zip(('dataset','budget_kib','backend'),key)) | dict(
            observations=len(rows),model_selection_seconds_median=med_model,
            grid_selection_seconds_median=med_grid,
            grid_model_median_time_ratio=med_grid/med_model,
            paired_grid_model_time_ratio_median=median([r['grid_selection_seconds']/r['model_selection_seconds'] for r in rows]),
            tods_selection_seconds_median=median([r['tods_selection_seconds'] for r in rows]),
            model_sketch_payload_bytes=5128,
            replay_trace_bytes_min=min(r['learning_trace_bytes'] for r in rows),
            replay_trace_bytes_max=max(r['learning_trace_bytes'] for r in rows),
            replay_trace_bytes_median=median([r['learning_trace_bytes'] for r in rows]),
            shared_candidate_build_seconds=matching[0]['shared_candidate_build_seconds'],
            candidate_count=rows[0]['candidate_count']))
    memory = []
    for key in sorted(settings):
        rows = [r for r in raw if tuple(r[k] for k in ('dataset','budget_kib','backend')) == key]
        cached = [r for r in rows if r['cache_capacity'] > 0]
        memory.append(dict(zip(('dataset','budget_kib','backend'),key)) | dict(
            observed_configurations=len(rows), filter_state_bytes_min=min(r['actual_filter_state_bytes'] for r in rows),
            filter_state_bytes_max=max(r['actual_filter_state_bytes'] for r in rows),
            member_index_bytes=rows[0]['member_index_bytes'],
            filter_plus_index_bytes_max=max(r['actual_filter_state_bytes']+r['member_index_bytes'] for r in rows),
            cache_bytes_min=min((r['cache_allocated_bytes'] for r in cached),default=0),
            cache_bytes_max=max((r['cache_allocated_bytes'] for r in cached),default=0),
            allocated_bits_per_capacity_min=min((r['cache_allocated_bytes']*8/r['cache_capacity'] for r in cached),default=None),
            allocated_bits_per_capacity_max=max((r['cache_allocated_bytes']*8/r['cache_capacity'] for r in cached),default=None),
            actual_bits_per_occupied_median=median([r['cache_bits_per_occupied'] for r in cached if r['cache_occupied']>0])))
    e2e, e2e_meta, e2e_status = [], [], []
    for ds in ('cod','caida'):
        path = RESULTS / 'end_to_end_fixed' / f'end_to_end_{ds}.json'
        obj = read(path) if path.exists() else {}
        part = obj.get('rows',[])
        complete = len(part) == 16 and len({(r['budget_kib'],r['workload'],r['positive_fraction'],r['placement']) for r in part}) == 16
        e2e_status.append(dict(dataset=ds,completed=complete,rows=len(part)))
        if complete:
            assert all(r['false_negatives'] == 0 for r in part)
            assert all(r['actual_filter_state_bytes'] <= r['budget_kib']*1024 for r in part)
            e2e.extend(part)
            e2e_meta.append(obj['metadata'])
            sources.append(str(path.relative_to(ROOT)))
    pairs = defaultdict(dict)
    for row in e2e:
        pairs[tuple(row[k] for k in ('dataset','budget_kib','workload','positive_fraction'))][row['placement']] = row
    placement = []
    projected = []
    for key, paths in sorted(pairs.items()):
        b,a = paths['cache_before'],paths['cache_after']
        item = dict(zip(('dataset','budget_kib','workload','positive_fraction'),key))
        item.update(before_mean_query_ns=b['mean_query_ns'],after_mean_query_ns=a['mean_query_ns'],
                    before_throughput_qps=b['measured_throughput_qps'],after_throughput_qps=a['measured_throughput_qps'],
                    before_false_positives=b['false_positives'],after_false_positives=a['false_positives'],
                    before_fpr=b['fpr'],after_fpr=a['fpr'],
                    before_backend_access_rate=b['accepted']/b['evaluated_queries'],
                    after_backend_access_rate=a['accepted']/a['evaluated_queries'],
                    before_minus_after_fp=b['false_positives']-a['false_positives'],
                    before_false_negatives=b['false_negatives'],after_false_negatives=a['false_negatives'])
        placement.append(item)
        for r in (b,a):
            for projection in r['backend_projections']:
                projected.append(dict(zip(('dataset','budget_kib','workload','positive_fraction'),key)) |
                                 dict(placement=r['placement'],cpu_measured_mean_query_ns=r['mean_query_ns'],**projection))
    summary = dict(generated_local=datetime.now().isoformat(timespec='seconds'),
                   completed_run_status=status,end_to_end_status=e2e_status,
                   source_files=sources,rows=len(raw),aggregates=aggregates,
                   workload_comparisons=comparisons,setting_summary=setting_summary,
                   selection_efficiency=efficiency,memory=memory,
                   end_to_end_pairs=placement,backend_projections=projected,
                   end_to_end_metadata=e2e_meta,
                   all_filter_states_within_budget=all(r['actual_filter_state_bytes']<=r['budget_kib']*1024 for r in raw),
                   all_recorded_member_false_negatives_zero=all(r['member_false_negatives']==0 for r in raw))
    save(RESULTS / 'summary_v2.json',summary)
    for name, rows in [('workload_metrics',aggregates),('workload_comparisons',comparisons),
                       ('setting_summary',setting_summary),('selection_efficiency',efficiency),
                       ('memory_audit',memory),('end_to_end_placements',placement),('backend_projections',projected)]:
        write_csv(ROOT/'tables'/f'{name}.csv',rows)
    render(summary)
    print(json.dumps(dict(rows=len(raw),complete_runs=sum(r['completed'] for r in status),
                          total_runs=len(status),e2e_complete=sum(r['completed'] for r in e2e_status),
                          report=str(ROOT/'REPORT.md')),ensure_ascii=False,indent=2))


def render(s):
    complete = sum(r['completed'] for r in s['completed_run_status'])
    final = complete == 8 and all(r['completed'] for r in s['end_to_end_status'])
    lines = ['# Windows 补充实验结果', '',
             f"生成时间：{s['generated_local']}（本机）。状态：{'全部预声明结果已汇总' if final else '进行中，仅汇总已完成运行'}。",'']
    if final:
        lines += ['完成542条有效误报实验结果、2条明确不可行的固定48树基线记录，以及32条端到端计时结果。记录和算术核验见 [suite-verification.json](evidence/suite-verification.json)。','']
    if s['workload_comparisons']:
        ratios = [r['model_grid_ratio'] for r in s['workload_comparisons']]
        loses = sum(x>1+1e-12 for x in ratios)
        wins = sum(x<1-1e-12 for x in ratios)
        ties = len(ratios)-loses-wins
        worst = max(s['workload_comparisons'],key=lambda r:r['model_grid_ratio'])
        lines += [f"**当前证据不支持直接宣称误报流选择器在效果上优于学习期网格调优。** 在已完成的{len(ratios)}个数据集×预算×后端×负载比较中，误报流模型胜{wins}、平{ties}、负{loses}；(平均FP+1)/(网格平均FP+1)中位数为{fmt(median(ratios))}，最大{fmt(max(ratios))}。",'',
                  f"最坏情况为 {worst['dataset']} {worst['budget_kib']}KiB / {worst['backend']} / {worst['workload']}：模型平均FP={fmt(worst['model_fp_mean'])}，网格={fmt(worst['grid_fp_mean'])}，每百万次查询多{fmt(worst['model_minus_grid_fp_per_million'])}次误报。比例大时应结合这个绝对差值判断。",'']
    lines += ['紧凑缓存和真实打包后的过滤器状态可以控制在分配预算内；额外成员检索索引、查询输入、训练/搜索工作集、解释器和JIT不在该KiB状态预算内。因此结论只适用于“同过滤器状态预算”，不能写“整个系统同内存”。COD私有成员哈希索引还需24,000,000B。','',
              '## 完成范围与口径','',
              '| 数据集 | CLOCK | 全局LRU |','|---|---|---|']
    for ds in EXPECTED_DATASETS:
        states = [next(r for r in s['completed_run_status'] if r['dataset']==ds and r['backend']==b) for b in EXPECTED_BACKENDS]
        lines.append(f"| {ds} | "+' | '.join(('完成，' if r['completed'] else '运行中/待运行，')+str(r['rows'])+'行' for r in states)+' |')
    lines += ['', '两条比较线各自公平：CLOCK为实际位打包四路商桶、40bit最长安全前缀、长度字段和引用位；全局LRU为完整64bit哈希、开放寻址表和双向链表。后端之间空间布局不同，不能把差距仅归为淘汰策略。CLOCK保存可变的安全前缀长度，但每槽余数预留固定最大宽度，并非真正支持任意变长余数的完整quotient filter。','',
              '共同设置：14种候选树数、9种缓存比例{0,1%,2%,5%,10%,20%,30%,40%,60%}，双方使用相同可行候选；全部方法共同预留5128B统计负载。合成重复查询1M、3种子；每key一次和高分全新查询维持原key数量；真实流按完整时间顺序、1次。前25%学习，后75%评价；选择后所有方法从空缓存开始尾段。与原10M×5种子实验规模不同。','',
              '## 误报效果','',
              '表内先对种子FP取均值，再计算(平均FP+1)比值。小于1表示误报流模型更好。中位数和最大值按该设置的不同负载计算，不是按查询量加权。','',
              '| 数据集 | KiB | 后端 | 负载数 | 模型/网格 中位/最坏 | 模型/Gama 中位/最坏 | 模型对网格 胜/平/负 |','|---|---:|---|---:|---:|---:|---:|']
    for r in s['setting_summary']:
        lines.append(f"| {r['dataset']} | {r['budget_kib']} | {r['backend']} | {r['workloads']} | {fmt(r['model_grid_ratio_median'])} / {fmt(r['model_grid_ratio_worst'])} | {fmt(r['model_gama_ratio_median'])} / {fmt(r['model_gama_ratio_worst'])} | {r['model_beats_grid']}/{r['model_ties_grid']}/{r['model_loses_grid']} |")
    lines += ['', '逐负载、逐方法的FP/FPR均值、样本标准差、种子数及选择配置见 [workload_metrics.csv](tables/workload_metrics.csv)；模型、网格、TODS式网格和Gama的并排数据见 [workload_comparisons.csv](tables/workload_comparisons.csv)。真实轨迹只有一次运行，标准差留空。','',
              '## 选择成本','',
              '以下为剔除JIT后的选择耗时中位数。模型时间包含草图统计与模型选择；网格时间包含逐候选回放及选择。候选结构构建为双方共享的单独成本，不能把下表时间比称为整个训练或部署的加速比。缓存比例为有限9点网格；未测试更密搜索。','',
              '| 数据集 | KiB | 后端 | 模型s | 网格s | 两中位数之比 | TODS式s | 共享构建s | 可行候选数 |','|---|---:|---|---:|---:|---:|---:|---:|---:|']
    for r in s['selection_efficiency']:
        lines.append(f"| {r['dataset']} | {r['budget_kib']} | {r['backend']} | {fmt(r['model_selection_seconds_median'],6)} | {fmt(r['grid_selection_seconds_median'],6)} | {fmt(r['grid_model_median_time_ratio'])} | {fmt(r['tods_selection_seconds_median'],6)} | {fmt(r['shared_candidate_build_seconds'])} | {r['candidate_count']} |")
    lines += ['', '统计状态有效负载实测5128B（两个uint8 HLL、三份uint32 Space-Saving字段及uint64计数器）；数组头另计入过滤器状态。此数不是整个学习进程内存。顺序网格重放保存学习期int64轨迹；其字节数、共享候选分数/结构构建的成本须与草图分开。', '',
              '| 数据集 | KiB | 后端 | 草图负载B | 重放轨迹B中位数 | 轨迹范围B |','|---|---:|---|---:|---:|---:|']
    for r in s['selection_efficiency']:
        lines.append(f"| {r['dataset']} | {r['budget_kib']} | {r['backend']} | 5,128 | {fmt(r['replay_trace_bytes_median'],0)} | {r['replay_trace_bytes_min']:,}–{r['replay_trace_bytes_max']:,} |")
    lines += ['', '网格可改为边到达边并行维护多个候选，从而不保存轨迹，但会消耗多个候选的状态；本实验测量的是顺序重放实现。主方法也仍需候选构建工作集，因此“5KB即可完成全部训练”不成立。TODS式仅修正原项目PLBF+缓存的比例选择，不能声称完整复现TODS论文。','',
              '## 实际状态内存','',
              '| 数据集 | KiB | 后端 | 状态B最小–最大 | 额外成员索引B | 缓存B最小–最大 | 每容量槽bit最小–最大 |','|---|---:|---|---:|---:|---:|---:|']
    for r in s['memory']:
        lines.append(f"| {r['dataset']} | {r['budget_kib']} | {r['backend']} | {r['filter_state_bytes_min']:,}–{r['filter_state_bytes_max']:,} | {r['member_index_bytes']:,} | {r['cache_bytes_min']:,}–{r['cache_bytes_max']:,} | {fmt(r['allocated_bits_per_capacity_min'],2)}–{fmt(r['allocated_bits_per_capacity_max'],2)} |")
    lines += ['', '缓存实际分配包含空槽、查找/替换元数据、格式头和唯一NumPy数组对象头。“每容量槽bit”以最大槽数为分母；真实已占用条目更少时，每条分摊成本更高，详见 [memory_audit.csv](tables/memory_audit.csv)。本实现不承诺或沿用历史27.5–29bit/条。模型为实际可执行数组，BF为真正打包位图，导航和数组头已计。成员集合固定；动态插入要在发布成员前失效冲突缓存。','',
              f"已完成重跑中，记录的成员漏判为0：{s['all_recorded_member_false_negatives_zero']}；全部所报过滤器状态在预算内：{s['all_filter_states_within_budget']}。缓存安全性还依赖独立碰撞/成员查询测试，不能用负查询FPR表替代。",'',
              '## 端到端查询成本','',
              '固定48树、10%缓存；COD256/1024KiB、Caida128/256KiB；均匀与Zipf1.1-1万，正例10%/50%。每配置1M混合查询、前25%预热；尾段3次实测平均时间取中位数。包含在线哈希、树遍历、packed BF、缓存更新、插入时成员索引查找和草图更新；不包含原对象特征抽取、模型构建或真实磁盘/网络。','',
              '| 数据集 | KiB | 负查询负载 | 正例 | 缓存在前ns | 缓存在后ns | 在前/在后 Mqps | 尾段FP在前/在后 |','|---|---:|---|---:|---:|---:|---:|---:|']
    for r in s['end_to_end_pairs']:
        lines.append(f"| {r['dataset']} | {r['budget_kib']} | {r['workload']} | {r['positive_fraction']:.0%} | {fmt(r['before_mean_query_ns'],1)} | {fmt(r['after_mean_query_ns'],1)} | {fmt(r['before_throughput_qps']/1e6)} / {fmt(r['after_throughput_qps']/1e6)} | {r['before_false_positives']:,}/{r['after_false_positives']:,} |")
    if not s['end_to_end_pairs']:
        lines += ['', '端到端测量尚未完成，不以旧微基准约7ns替代。']
    lines += ['', '两个放置的误报独立测量。安全前缀可能顺便挡住其他负例，并改变CLOCK状态，因此不预先强制它们相等。后端1/10/100μs采用“实测CPU时间+后端访问率×假定后端延迟”的线性投影；均为推算，不是I/O实测。全部档位详见 [backend_projections.csv](tables/backend_projections.csv)。','',
              '## 原版Stacked与历史结果审计','',
              '以下只审计历史运行，不混入本轮严格预算排名。actual_bits/budget_bits>1的运行显式标超预算；未宣称修改原版Stacked后已经压回预算。','',
              '| 数据集 | 标称KiB | 历史运行 | 超预算运行 | 实际KiB最小–最大 | 实际/标称最小–最大 |','|---|---:|---:|---:|---:|---:|']
    audit_path = RESULTS/'audit_existing.json'
    if audit_path.exists():
        for r in read(audit_path)['stacked_summary']:
            lines.append(f"| {r['dataset']} | {r['budget_kib']} | {r['runs']} | {r['over_budget_runs']} | {fmt(r['budget_kib']*r['min_actual_budget_ratio'],2)}–{fmt(r['budget_kib']*r['max_actual_budget_ratio'],2)} | {fmt(r['min_actual_budget_ratio'],5)}–{fmt(r['max_actual_budget_ratio'],5)} |")
    lines += ['', '原微基准16,384槽×16B=262,144B，约为标称10%缓存定额的10倍；原代码用uint8存逻辑BF位且草图用int64数组，均不能当作KiB内存的物理实现。详细源码依据见 [review-audit.md](evidence/review-audit.md)。历史MAWI2020已被用于实验10–14和预处理检查，不能重标为本次未接触留出集。','',
              '## 新MAWI2021与冻结记录','']
    mawi = [r for r in s['setting_summary'] if r['dataset']=='mawi2021_flow']
    if mawi:
        lines += ['本轮使用预声明2021-04-14日期、前120,000,000压缩字节、最多10M完整包。实际包含5,005,617个完整包，保留4,871,259个TCP/UDP包；截断gzip尾部记录后丢弃不完整包。按IP头读取真实总长度，区别于历史tcpdump净载荷加固定头长的近似。数据准备未训练模型，首次模型评估在本轮冻结之后进行。', '',
                  '所有40/48/64KiB及两种后端均按预声明参数报告。40KiB下固定48树的TODS式基线不能装入物理预算，标为不可行，不降低计费或临时改树数。首次执行在尚未写出尾段指标前因该空候选集合崩溃，随后仅增加不可行基线的记录和跳过逻辑；失败日志与修改前源码保存在evidence/failures。原冻结记录保留，并增加holdout-freeze-amendment.json；因此不能宣称无故障、零重启的严格一次执行。候选、模型选择和评估参数没有调整。', '',
                  '来源哈希、字节数和解析方式见 [mawi2021-source.json](data/mawi2021-source.json)，代码/协议冻结记录见plan目录；修复说明见 [holdout-repair.md](evidence/holdout-repair.md)。']
        lines += ['', '| KiB | 后端 | 模型FP | 学习期网格FP | Gama无缓存FP | 模型每百万查询FP |', '|---:|---|---:|---:|---:|---:|']
        for r in s['workload_comparisons']:
            if r['dataset']=='mawi2021_flow':
                lines.append(f"| {r['budget_kib']} | {r['backend']} | {fmt(r['model_fp_mean'],0)} | {fmt(r['grid_fp_mean'],0)} | {fmt(r['gama_fp_mean'],0)} | {fmt(r['model_fp_per_million'])} |")
    else:
        lines += ['新MAWI2021数据已取得，尚未在本报告纳入完成的冻结评估。它不能由历史MAWI2020表格替代；最终只有冻结后的完整JSON进入此处。']
    lines += ['', '## 可写与不可写的结论','',
              '- 可以报告：真实打包的缓存/模型/BF状态、给定预算和查询前缀下的学习期选择效果、选择耗时与统计状态、含正例和反馈的两种端到端放置成本。',
              '- 若模型与网格误报接近，可将贡献收窄为较小统计状态和较低选择成本；存在明显坏例时，不能只宣传中位效果而省略最坏退化。',
              '- 不可以报告：全部系统RSS同KiB预算、通用28bit缓存条目、所有负载上模型必胜网格、真实后端I/O吞吐、动态成员插入已完整实现，或所有历史实验完整复现。',
              '- 所有代码与结果留在新目录。原目录内容保护证据为 [protected-verification.json](evidence/protected-verification.json)。','',
              '真实flow数据还保留原项目的离线定义：每条流的长度均值/最小/最大由整个捕获前缀聚合，查询使用这些固定特征。它检验跨数据集的过滤器选择，不能据此宣称完成了只使用当时已到达包的因果在线流分类实验。','',
              '机器可读汇总：[summary_v2.json](results/summary_v2.json)。实验协议：[experiment-protocol.md](plan/experiment-protocol.md)。报告可用 `python windows_research/src/summarize_results.py` 由已完成JSON重建。','']
    protection=ROOT/'evidence'/'protected-verification.json'
    if protection.exists():
        p=read(protection)
        assert p['unchanged'] is True
        lines += [f"最终保护核验通过：research/与learned_adaptive_hybrid/共{p['before_files']:,}个文件逐项SHA256及修改时间一致；新增、缺失、内容变化和修改时间变化均为0。",'']
    (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__ == '__main__':
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    summarize()
