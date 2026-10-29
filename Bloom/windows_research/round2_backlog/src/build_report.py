"""Readable Chinese report derived from preserved, verified result JSON."""
from pathlib import Path
import json,csv,collections,statistics,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def csvout(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/'tables'/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])
def run():
    verified=load(ROOT/'results'/'verification.json');assert verified['status']=='passed'
    raw=[r for p in (ROOT/'results'/'main').glob('*/*.json') for r in load(p)['rows']]
    settings=collections.defaultdict(dict)
    for r in raw:settings[r['dataset'],r['budget_kib'],r['workload'],r['seed']][r['method']]=r
    synthetic=[v for k,v in settings.items() if not k[0].endswith('_flow')]
    wins=sum(v['StreamModel']['fp_tail']<v['LearnGrid']['fp_tail'] for v in synthetic);losses=sum(v['StreamModel']['fp_tail']>v['LearnGrid']['fp_tail'] for v in synthetic)
    descriptive=[]
    for ds,kib in sorted({k[:2] for k in settings}):
        cases=[v for k,v in settings.items() if k[:2]==(ds,kib)]
        total={m:sum(v[m]['fp_tail'] for v in cases) for m in ('Gama','StreamModel','LearnGrid','BFCacheGrid')}
        descriptive.append(dict(dataset=ds,budget_kib=kib,cases=len(cases),**{m+'_fp_sum':v for m,v in total.items()},model_grid_smoothed_ratio=(total['StreamModel']+1)/(total['LearnGrid']+1)))
    csvout('setting_descriptive_fp.csv',descriptive)
    import fast_cache as F
    allocation=[]
    for r in raw:
        if not r['cache_allocated_bytes']:continue
        budget=r['cache_allocated_bytes'];probation=256*9+2*F.ARRAY_HEADER if r['method']=='SkiQFAdmission2' else 0
        spec=F.layout(budget-probation)
        allocation.append(dict(dataset=r['dataset'],budget_kib=r['budget_kib'],workload=r['workload'],seed=r['seed'],method=r['method'],
            cache_allocated_bytes=budget,cache_reserved_bytes=r['cache_reserved_bytes'],returned_to_bf_bytes=r['cache_returned_bytes'],
            prefix_capacity=spec['slots'],occupied=r['cache_occupied'],probation_bytes=probation,
            bytes_per_provisioned_prefix_slot=budget/spec['slots'] if spec['slots'] else None,
            bytes_per_occupied_prefix_slot=budget/r['cache_occupied'] if r['cache_occupied'] else None,
            required_member_index_bytes=r['member_index_bytes']+F.ARRAY_HEADER))
    csvout('cache_allocation_audit.csv',allocation)
    examples=[r for r in allocation if r['method']=='StreamModel' and r['seed']==0 and r['workload']=='uniform-1万' and (r['dataset'],r['budget_kib']) in [('cod',256),('caida',128),('shalla',256),('url',64)]]
    history=load(ROOT.parent/'results'/'audit_existing.json');csvout('historical_stacked_memory.csv',history['stacked_rows'])
    live=[r for p in (ROOT/'results'/'live').glob('*.json') for r in load(p)['rows']]
    livecases=collections.defaultdict(dict)
    for r in live:livecases[r['dataset'],r['budget_kib'],r['workload'],r['positive_fraction']][r['method'],r['placement']]=r
    perf=[]
    for key,methods in livecases.items():
        gama=methods['Gama','before']
        for (name,placement),r in methods.items():
            for g,b in zip(gama['backend_projections'],r['backend_projections']):
                perf.append(dict(dataset=key[0],budget_kib=key[1],workload=key[2],positive_fraction=key[3],method=name,placement=placement,backend_us=b['backend_us'],projected_speedup=g['projected_ns']/b['projected_ns'],cpu_speedup=gama['mean_query_ns']/r['mean_query_ns'],false_positives=r['fp'],queries=r['evaluation_queries']))
    csvout('live_projected_speedups.csv',perf)
    latency=[]
    sql=load(ROOT/'results'/'sqlite_backend.json')
    for method in ('NoFilter','Gama','StreamModel','LearnGrid'):
        rows=[r for r in sql['rows'] if r['method']==method]
        latency.append(dict(method=method,median_query_ns=statistics.median(r['mean_query_ns'] for r in rows),backend_gets=rows[0]['backend_gets'],backend_misses=rows[0]['backend_misses'],repeats=len(rows)))
    csvout('sqlite_metrics.csv',latency)
    sketch=[]
    for p in (ROOT/'results'/'live').glob('*.json'):
        o=load(p)
        for s in o['selections']:sketch.append(dict(dataset=p.stem,**{k:s[k] for k in ('budget_kib','workload','positive_fraction','learning_queries','learning_negative_queries','model_seconds','grid_seconds','retained_grid_trace_bytes','model_statistics_payload_bytes')}))
    csvout('selection_costs_current_grid.csv',sketch)
    ablation=[r for p in (ROOT/'results'/'ablations').glob('*.json') for r in load(p)['rows']]
    ag=collections.defaultdict(list)
    for r in ablation:ag[r['dataset'],r['workload'],r['task'],r['variant'],r.get('learning_fraction',.25)].append(r)
    from scipy.stats import t as student
    import math
    absummary=[]
    for key,values in sorted(ag.items()):
        rates=[r['fpr'] for r in values];mean=statistics.mean(rates);sd=statistics.stdev(rates) if len(rates)>1 else None
        half=float(student.ppf(.975,len(rates)-1)*sd/math.sqrt(len(rates))) if sd is not None else None
        absummary.append(dict(dataset=key[0],workload=key[1],task=key[2],variant=key[3],learning_fraction=key[4],runs=len(values),fp_mean=statistics.mean(r['fp_tail'] for r in values),fpr_mean=mean,fpr_std=sd,
            ci95_low=max(0.,mean-half) if half is not None else None,ci95_high=min(1.,mean+half) if half is not None else None))
    csvout('ablation_metrics.csv',absummary)
    topflow=[]
    for ds in ('caida_flow','mawi2021_flow'):
        primary={r['method']:r['fp_tail'] for r in raw if r['dataset']==ds and r['budget_kib']==24}
        top={r['variant']:r['fp_tail'] for r in ablation if r['dataset']==ds and r['task']=='A2'}
        topflow.append([ds,primary['StreamModel'],top['top3'],top['top5'],top['top10'],primary['LearnGrid']])
    task_evidence={
        'F1':'results/main; tables/main_metrics.csv','F2':'results/main（cache_returned_bytes）','F3':'results/main（Fixed48Grid）',
        'F4':'results/F4_mawi_hotspots.json','M1':'results/main; results/verification.json','M2':'cache/url/preparation.json; cache/shalla/preparation.json; data/*-source.json',
        'M3':'tables/main_metrics.csv; tables/paired_comparisons.csv; tables/aqf_metrics.csv','B1':'results/stacked; tables/main_metrics.csv',
        'B2':'tables/historical_stacked_memory.csv','B3':'results/aqf; results/aqf_preflight.json; tables/aqf_metrics.csv',
        'B4':'results/main（SkiQFAdmission2）','B5':'results/main（BFCacheGrid）','B6':'evidence/B6-gama-reproduction.md',
        'E1':'results/live; tables/live_projected_speedups.csv','E2':'results/sqlite_backend.json; tables/sqlite_metrics.csv',
        'R1':'cache/*_flow/preparation.json; results/verification.json','R2':'results/main/caida_flow; results/main/mawi2021_flow; results/hash_sensitivity',
        'R3':'plan/final-holdout-freeze.json; results/main/mawi2022_flow; results/stacked/mawi2022_flow',
        'A1':'results/ablations; evidence/A1-original-variable-windows','A2':'results/ablations（A2）','A3':'results/ablations（A3）',
        'A4':'results/ablations（A4）; evidence/A4-injected-prehash-collision.json','A5':'results/live（before/after）','A6':'results/ablations（A6）',
        'O5':'results/dynamic_members.json','O6':'results/recalibration_cod.json; results/recalibration_caida.json'}
    notes={'B2':'采用清单允许的倍率标注方案；由原实现内部记账反推，非本轮物理堆内存；旧超预算结果不进入严格同预算排名','B6':'采用清单允许的明确说明复现方式方案；并非逐字复现原作者Hybrid','E1':'C臂按用户要求排除；后端延迟为投影','E2':'实际SQLite文件KV，OS缓存未清空','R3':'首次训练/评估前冻结执行代码；只报告固定日期固定配置','A3':'两组同布局控制及跨编码实现敏感性，不能混为纯替换策略差异','O5':'顺序发布正确性，不覆盖并发原子性','O6':'使用过去窗口20MB轨迹；重建双状态峰值另报'}
    tasks=[]
    for t in load(ROOT/'plan'/'backlog.json')['tasks']:
        if t['in_scope']:tasks.append(dict(id=t['id'],title=t['title'],source_row=t['source_row'],status='completed',evidence=task_evidence[t['id']],qualification=notes.get(t['id'],'')))
    assert len(tasks)==26
    csvout('task_status.csv',tasks);(ROOT/'results'/'task_status.json').write_text(json.dumps(tasks,ensure_ascii=False,indent=2),encoding='utf-8')
    h=load(ROOT/'results'/'F4_mawi_hotspots.json')['rows']
    d=load(ROOT/'results'/'dynamic_members.json')
    fpflow=[[r['dataset'],r['budget_kib'],r['method'],r['fp_tail'],f"{100*r['fpr']:.4f}%",r['trees'],r['frac']] for r in raw if r['dataset'].endswith('_flow') and r['method'] in ('Gama','StreamModel','LearnGrid')]
    stats=load(ROOT/'results'/'main_summary.json')
    stackcmp=[r for r in stats['comparisons'] if r['baseline']=='LearnedStacked_LearnTune']
    stackloss=sum(r['delta_fpr_mean']>0 for r in stackcmp);stackwin=sum(r['delta_fpr_mean']<0 for r in stackcmp)
    aqfraw=[r for p in (ROOT/'results'/'aqf').glob('*.json') for r in load(p)['rows']]
    aqftable=[]
    for ds in sorted({r['dataset'] for r in aqfraw}):
        values=[r for r in aqfraw if r['dataset']==ds]
        aqftable.append([ds,values[0]['budget_kib'],len(values),sum(r['fp_tail'] for r in values),sum(r['gama_fp'] for r in values),max(r['filter_allocated_bytes'] for r in values),max(r['reverse_map_allocated_bytes'] for r in values)])
    memory=load(ROOT/'evidence'/'process-memory-peaks.json')['processes'];rss=max(r['observed_peak_bytes'] for r in memory)
    reconfig=[]
    for ds in ('cod','caida'):
        rows=load(ROOT/'results'/f'recalibration_{ds}.json')['rows']
        reconfig.append([ds,sum(r['frozen_fp'] for r in rows),sum(r['periodic_fp'] for r in rows),f"{sum(p['calibration_seconds']+p['rebuild_seconds'] for r in rows for p in r['intervals']):.3f}",max(r['atomic_rebuild_peak_filter_state_bytes'] for r in rows)])
    report=f'''# PassCache 第二轮：非 C 实验结果

源任务为用户提供的 `PassCache全部待办.xlsx` 总任务表，本轮完成26项实验；C1–C5及理论、论文写作、仓库权限、联系他人等非实验任务未纳入。实验均保存在本目录。结论是：**缓存有效，但当前误报流模型选配置的精度经常不如学习期网格，现有证据不足以声称它达到网格效果。** 这不是新增C方法的验证，也不是可投稿性或整体净收益结论。

## 1. 完成范围与数据

核验计数：{json.dumps(verified['counts'],ensure_ascii=False)}。

重复型负载恢复10,000,000查询、5个配对种子；每key一次和50,000全新高分负例保留其原始长度。模型、划分固定；学习前25%，评估尾75%冷缓存。真实轨迹不伪造5次独立重复。地址特征流程覆盖Caida、MAWI2021、首次冻结后评价的MAWI2022；旧五特征MAWI仅用于F4历史审计。

完整URL原表651,191行、去重641,119个URL。6个URL出现善恶冲突，采用“任何恶意标签即成员”的集合并集口径；早期错误的首行标签缓存和结果保存在`cache/url_first_label_invalid`与`results/invalid_url_first_label`，没有混入最终表。Shalla与完整URL均独立训练本轮模型。所有训练负例、验证负例、测试负例交集为零。

## 2. 主结果与对网格的判断

在{len(synthetic)}个合成负载/种子/预算配对中，StreamModel的FP少于LearnGrid有{wins}个、多于有{losses}个、相等有{len(synthetic)-wins-losses}个。这是描述性计数，不是独立数据集数量。下表合计各预声明负载的FP，包含不同长度once/fresh；比例仅便于定位异常，正式比较应查逐负载均值、区间和配对差，不能作为跨负载显著性或上线收益。

{table(['数据','KiB','案例数','Gama FP合计','模型 FP合计','网格 FP合计','(模型+1)/(网格+1)'],[[r['dataset'],r['budget_kib'],r['cases'],r['Gama_fp_sum'],r['StreamModel_fp_sum'],r['LearnGrid_fp_sum'],f"{r['model_grid_smoothed_ratio']:.3f}"] for r in descriptive])}

COD1024、URL128/256的模型/网格差距尤其明显，不能以少量高重复场景代替全矩阵。当前可保留“负缓存处理重复误报”的方向，但贡献3既不能写效果更好，也不能未经新证据写为5KB达到网格效果。A2的top3/5/10实际结果另列，用于判断有限回放是否值得；不把其结果反馈到已固定主方法。

{table(['真实轨迹','KiB','方法','尾段FP','FPR','树数','比例'],fpflow)}

五种子的95%t区间是固定数据/固定模型下工作负载种子的不确定性；配对检验使用32种符号翻转，双侧最小p=.0625，因此不能在.05下声称显著。主比较族按预定范围Holm校正；fresh为确定序列，有效独立重复数1，不制造区间。真实轨迹同样仅描述，hash盐敏感性150条另表，不把5个hash当5条独立轨迹。

## 3. 内存口径与基线

Gama部署不扣5,128B草图；所有方法完成学习后都不保留草图。缓存采用word-packed quotient前缀布局，真实数组头、格式头、空槽、CLOCK/LRU/FIFO元数据均计费；缓存定额未用部分返还BF。此口径为实际部署数组与规定描述符，执行器包装对象、JIT和输入数据归宿主基础设施，不等于整个Python对象图。逐条组件和始终小于等于预算由核验脚本检查。每个实际选择的缓存容量、空槽、已用槽、每槽实测字节及返还BF字节另列于`tables/cache_allocation_audit.csv`；不继续沿用28bit/条的理想编码假设。

**KiB预算是过滤器部署状态预算，不是整个进程或全系统RAM。** 已校验缓存额外需要8×成员数+112B数组头的有序成员hash索引；Gama、静态Stacked不需要该索引。表中同时保留仿真进程统一分配的索引和方法必需索引。学习网格保留轨迹，模型统计payload5,128B外还有数组头、公共模型候选、数据、JIT等；观测到整进程最大RSS为{rss/1024**3:.2f}GiB，不能宣传整段学习仅5KB。`tables/selection_costs_current_grid.csv`用更新后的精确加速网格与模型并列计时；早期主实验较慢网格计时只作原始记录，不能用于夸大必要成本。

下表固定展示各数据第一主预算、uniform1万池、seed0的模型选择；不是所有设置的平均。小缓存的格式头和数组头摊销很高；已用条目成本还会随占用率升高。完整表逐行保留所有选择与空槽。

{table(['数据','KiB','缓存B','预留槽数','B/槽(含头和空槽)','必要校验索引B'],[[r['dataset'],r['budget_kib'],r['cache_allocated_bytes'],r['prefix_capacity'],f"{r['bytes_per_provisioned_prefix_slot']:.3f}",r['required_member_index_bytes']] for r in examples])}

真正普通BF+negative cache使用同一已校验缓存，在学习期调比例；Fixed48Grid明确只是固定48树的消融；SkiQFAdmission2是计费的二次准入实现，不冒充整篇SkiQF。Learned stacked以Gama验证选中的树数为底座，在学习期内部一半构建、一半选侧层比例与b2，最后用全部学习期重建，并加入零侧层退化选项，旧结果重新比较不接触尾段。

原版Stacked历史审计共{history['stacked_runs']}条，其中{history['stacked_over_budget_runs']}条超标，按旧实现内部记账反推的倍率逐条列于`tables/historical_stacked_memory.csv`；这是清单B2允许的标注路径，超预算历史数据不混入本轮严格预算排名。AdaptiveQF为上游C实现，经WSL原生编译实际运行342条，报告malloc实际分配和反查表；低预算是否连最小结构都装不下见`results/aqf_preflight.json`，高预算结果与同预算Gama同流比较，不能与低预算主表偷换比较。

B6按清单的说明路径完成：本轮复现为14个前缀树数搜索、100段PLBF、位打包实测状态，而原作者Hybrid用其独立搜索流程与pickle口径。详见`evidence/B6-gama-reproduction.md`。不能声称逐字复现原作者Hybrid的数字或调参时间。

学习调优Stacked与模型的{len(stackcmp)}个负载/预算均值比较中，模型更差{stackloss}个、更好{stackwin}个，相等{len(stackcmp)-stackloss-stackwin}个，同样不构成稳定优势。Stacked允许把学习期观察到的负例构建为部署BF；缓存方法按本协议在尾段冷启动。这种知识携带方式属于各自算法，选择与建层均不使用评估尾段。完整区间/配对差在主表，而非只展示模型胜出的设置。

{table(['AQF数据','KiB','案例数','AQF FP合计','同预算Gama FP合计','AQF堆状态最大B','反查表堆分配最大B'],aqftable)}

这里仍是混合长度负载的描述性合计；高预算和主表低预算不混排。反查表列是实际堆分配，Map包装本身以及宿主程序基础设施另属运行时对象，不能把这列冒充全进程内存。

## 4. MAWI旧标题数字审计

{table(['扣草图B','KiB','树数','误报总量','不同误报key','最热key占比'],[[r['sketch_reserved_bytes'],r['budget_kib'],r['trees'],r['fp_total'],r['distinct_fp_keys'],f"{r['top1_fraction']:.1%}"] for r in h])}

旧64KiB的299次FP全部来自一个BF热点。取消不应向Gama扣的草图后，同预算剩4次FP、2个key；旧“77倍”标题数字应撤回。BF位数与取模改变会换一批误报key，真实流按频率加权后的误报量不保证随预算单调；这不等于训练或测试数据相交。

## 5. 真实推理与实际KV后端

E1共80条路径，每条3次冷缓存尾段计时，COD256/1024、Caida128/256，10%/50%正查询、uniform/Zipf两类。执行hash、实时树遍历、BF、缓存、成员前缀校验与负反馈，原始分数与LightGBM最大误差小于1e-10；特征提取和输入I/O不在计时内。前置和后置用各方法自己的学习期选择配置，不能借用不匹配的FPR主表配置。1/10/100微秒后端是`CPU时间+真实访问率×设定延迟`的明确投影，不是实际磁盘测量。原始重复时长、命中、推理和后端访问次数均保留。

E2采用真实SQLite文件KV、同步SELECT、8MiB页缓存、mmap关闭，未刷新OS页缓存。每条评估100,000次请求、3轮轮转顺序，包含Python/Numba/SQL调度成本；不是冷盘延迟，也不能直接与E1融合内核的CPU单价互换。

{table(['方法','每次查询ns中位数','实际get次数/10万','实际miss次数','重复'],[[r['method'],f"{r['median_query_ns']:.1f}",r['backend_gets'],r['backend_misses'],r['repeats']] for r in latency])}

## 6. 消融与动态行为

A1所有5/10/25/50%学习前缀统一在同一最后50%冷窗口评价，间隙不用于预热；旧可变窗口结果另存。A2是模型排名中不同物理布局top3/5/10后精确回放；A3包括同布局CLOCK/桶FIFO、全局LRU/FIFO控制，跨前缀编码与full-hash实现的容量不同，不声称纯替换策略的因果效果；A6完整4种前缀×3种ways，以及细分0–2%比例网格。

{table(['24KiB真实流','纯模型FP','top3 FP','top5 FP','top10 FP','全网格FP'],topflow)}

top-k在部分失败例能明显降低观测误报量，但不据这两条轨迹宣布普遍等价。A2原始计时保存共享top10回放总成本，没有把这个总时长假装成单独top3或top5成本。Caida_flow24的纯模型选了零缓存，所以该点A3/A4的相等结果是配置退化，不是替换策略或key编码等价的证据。其它预声明设置与受控fixture照常保留。各消融的均值、标准差和95%t区间见`tables/ablation_metrics.csv`，真实单条轨迹不做区间。

A4中COD/Caida原始scalar64经双射hash，64位全hash本来就是精确标识；URL/flow无限原始键空间的预hash才有碰撞概率。真实数据未观察到碰撞，另用注入相同预hash的fixture证明：已校验前缀绕过不能安全缓存的负例，不校验64位缓存会误拒成员。这不是自然碰撞发生率测量。

O5在真实URL键上顺序增加{d['inserted_members']}个成员，先失效冲突缓存，再更新BF及索引，最后发布成员；实际移除{d['removed_cache_records']}条缓存记录，{d['final_member_checks']}次最终成员检查及在线查询均0FN。失效中位数{d['invalidation_median_ns']:.0f}ns、p95 {d['invalidation_p95_ns']:.0f}ns；排序索引维护中位数{d['index_maintenance_median_ns']:.0f}ns另报。此测试不证明并发原子发布或崩溃恢复。

O6在漂移流50/75%处仅用过去四分之一窗口批量校准，保留20MB轨迹，临时草图和原子替换新旧状态并集另计；不是恒定5KB在线更新，不是全程相同峰值内存。

{table(['数据','冻结FP合计(5种子)','周期FP合计','校准+重建s合计','替换状态峰值B'],reconfig)}

## 7. 独立验证和保留边界

MAWI2022-04-13固定前120,000,000压缩字节，下载后未训练/查看模型指标，最终执行代码与协议SHA先写入`plan/final-holdout-freeze.json`，之后才首次准备、训练并评价16/24/32KiB和学习Stacked。没有根据其结果回调参数，冻结后hash未变。数据是固定前缀而非整天全流量。

这是冻结方法在新数据划分上的一次评价，按同一协议在2022划分的训练/验证部分学习模型并选配置；不是把2021训练的模型直接迁移到2022，也不是无标签的新日在线评估。新数据未用于外层设计选择的保证限于本轮可核验的本地记录。

flow成员集合由协议离线定义；地址特征不使用整段聚合，但原始包本身含协议时，应用能直接区分UDP/TCP。因此它是静态成员集合/不透明key压力测试，不能据此声称完整在线网络分类方案的必要性或普遍净收益。

## 8. 完整性与逐项证据

源工作簿SHA256：`{verified['workbook_sha256']}`，原件未写入。`research/`与`learned_adaptive_hybrid/`共{verified['protected']['after_files']:,}文件、{verified['protected']['bytes']:,}字节，内容hash与修改时间均与本轮开始前一致。失败和被纠正的数据/调度尝试保留在evidence，未用删除失败重试来声称零重启。新代码、结果、表格、原始日志及模型hash全部在本轮目录；本轮没有自动推送新的研究内容到公开远端。

{table(['任务','状态','证据','限定'],[[r['id']+' '+r['title'],r['status'],r['evidence'],r['qualification']] for r in tasks])}

核验入口：`src/verify_round2.py`；结果`results/verification.json`。汇总入口`src/summarize_main.py`，报告入口`src/build_report.py`，绘图入口`src/make_figures.py`。候选构建共享成本、旧/新网格实现时间、部署/索引/学习/重建峰值均不混写。

结果图：[真实流FPR](figures/causal_trace_fpr.png)、[模型与网格FP](figures/model_grid_fp.png)、[端到端成本](figures/end_to_end.png)；同名SVG为矢量版本，源数据及图说明见`figures/data-manifest.md`。

主实验推进中存在已验证数值等价的实现加速和明确记录的修补，不能声称全研究过程始终使用同一冻结版本；严格的事前执行代码/协议冻结仅针对最终MAWI2022留出。最终源与模型/结果SHA保存在evidence中，以当前代码复现的时间开销应采用当前实现，不套用早期冗余版本的日志时间。
'''
    (ROOT/'REPORT.md').write_text(report,encoding='utf-8')
    (ROOT/'results'/'REPORT_COMPLETE.json').write_text(json.dumps(dict(experiments=26,excluded='C1-C5 and non-experimental tasks',verification='passed',counts=verified['counts'],report='REPORT.md',figure_visual_qa='pending'),ensure_ascii=False,indent=2),encoding='utf-8')
    print('REPORT COMPLETE',len(tasks),'tasks',flush=True)
if __name__=='__main__':run()
