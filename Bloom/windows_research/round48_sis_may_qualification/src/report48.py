import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data48 import *
import statistics,csv


def report():
    check();m=json.loads((ROOT/'results/data.json').read_text());rows=[json.loads((ROOT/f'results/seed{s}_diagnostic.json').read_text()) for s in SEEDS];assert all(r['status']=='complete' for r in rows)
    reasons=[]
    for field,limit in (('members',10000),('negative_keys',1000),('retained_404_requests',10000)):
        if m[field]<limit:reasons.append(f'{field}<{limit}')
    if m['retained_404_fraction']<.9:reasons.append('404retention<.9')
    for r in rows:
        for field,limit in (('train_negative_keys',20),('validation_negative_keys',20),('learning_queries',1000),('tail_queries',1000)):
            if r[field]<limit:reasons.append(f'seed{r["seed"]}:{field}<{limit}')
    summary=dict(status='verified',eligible_for_method_comparison=not reasons,ineligibility_reasons=reasons,diagnostics=rows,raw_line_limit=MAX_LINES,raw_lines=m['raw_lines'],whole_month_analyzed=False,method_FP_evaluated=False,business_record_existence_inferred=False,raw_data_published=False,prepared_sha256=m['prepared_sha256'])
    save(ROOT/'results/qualification.json',summary)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/'results/diagnostics.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    text=['# Round48：SIS五月固定前缀资格审计','','真实线上来源不等于已经证明RA需要或有优势。本轮只做资格，尚未测方法FP/SQL时间。任务是observed-success vs404的回溯稳定请求target子集，不从HTTP200推出真实业务record存在性。','','## 输入范围','',f'- 原五月文件13687894566B；官方MD5通过，仅提取五月。',f'- 按预声明读取前{MAX_LINES}原始行；实际{m["raw_lines"]}行、{m["parsed_GET"]}个成功解析GET。不是全月。',f'- 时间范围{m["minimum_timestamp"]}至{m["maximum_timestamp"]}；回退{m["time_reversals"]}次，未按time重新排序。',f'- HTTP状态计数：`{json.dumps(m["status_counts"],sort_keys=True)}`。认证/重定向/5xx不当negative。',f'- 稳定members={m["members"]}，negativekeys={m["negative_keys"]}，稳定404requests={m["retained_404_requests"]}，404保留率={m["retained_404_fraction"]:.6f}。',f'- 冲突keys={m["conflicting_keys"]}，排除冲突404={m["conflicting_404_requests"]}。','','## 资格结论','',f'进入后续方法矩阵：{not reasons}。',f'不合格原因：{reasons}。', '', '| seed | 开发AUC16 | learning negatives | tail negatives | 特征重叠比例 | learning重复比例 | firstcomponent规则拒绝tail | two-components规则拒绝tail |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in rows:text.append(f'| {r["seed"]} | {r["development_auc16"]} | {r["learning_queries"]} | {r["tail_queries"]} | {r["query_feature_overlap_fraction"]:.6f} | {r["learning_repeat_fraction"]:.6f} | {r["cheap_prefix1_tail_rejects"]} | {r["cheap_prefix2_tail_rejects"]} |')
    text+=['','Cheap-rule packed支持表的payload/header另见data.json，未计时也不保证可在小预算中免费使用；其支持集合来自同一静态member目录。若规则已排除大部分negative，不能把分类AUC直接当必须部署模型的证据。','','目录/冲突判定使用整个选定prefix，所以是回溯稳定子集；querystring保留为精确key，不输出userid/client/referrer/useragent。原系统200登录页/业务错误仍可能返回successstatus，仅凭access log不能建立真实KV对象存在性。原IP及身份字段不训练、不发布。','','没有看方法FP后换月/扩窗/降低门槛，六月等月仍未提取/解析。失败资格不等于RA输了或赢了；不要把未运行的五方法/端到端实验写成完成。论文未动，本批未push。','']
    with (ROOT/'results/report.md').open('x') as f:f.write('\n'.join(text))
    check();print('SIS_QUALIFICATION_VERIFIED',not reasons,reasons,flush=True)

if __name__=='__main__':report()
