"""Round 5: E1 (main table) + E2 (hindsight oracle) + E3 (prediction accuracy) + E6 (ablations).

One loop per (dataset, budget, workload, seed):
  E1  all seeds:   FastPLBF48, Gama, Gama(original), Gama+10%, LearnGrid, RA4
  E2  seeds 0..2:  every grid candidate on the evaluation segment -> fp_oracle
  E6  seeds 0..2:  RA4-noRepeat, -noSA, -noGT, -mix0.5, -mix1, -Table, RA-global
  E3  seed 0:      every RA4 candidate built and measured; predictions of the same structure by
                   RA4, RA4 without set-associative correction, noGT and mix0.5 predictors
Rows go to results/rows_<ds>_<kib>.csv (unified columns); E3 tables to results/e3_<ds>_<kib>.jsonl.
"""
import argparse
import csv
import json
import os
import resource
import subprocess
import time
from pathlib import Path
import numpy as np
import engine5 as E5
import ra5 as RA

ROOT = Path(__file__).resolve().parents[1]
OB = ROOT.parents[1] / 'original_baselines'
COLS = ('dataset,budget_kib,workload,zipf_s,pool,seed,method,allocator,trees,cache_reserved_bytes,cache_alloc_bytes,'
        'model_bytes,bf_bytes,metadata_bytes,overhead_bytes,total_bytes,fp_tail,fpr_tail,fp_oracle,pred_fp,'
        'cache_hit_rate,t_train_s,t_score_s,t_select_s,t_build_s,learn_state_bytes,peak_rss_bytes,query_ns_mean,'
        'query_ns_p50,query_ns_p99,backend_calls,e2e_ms_mean,e2e_ms_p99,code_commit,hardware').split(',')
Cfg = RA.Config
ABLATIONS = {'RA4-noRepeat': Cfg(new_mix=0., mode='norepeat'), 'RA4-noSA': Cfg(new_mix=0., setassoc=False),
             'RA4-noGT': Cfg(new_mix=0., gt=False), 'RA4-mix0.5': Cfg(new_mix=.5), 'RA4-mix1': Cfg(new_mix=1.),
             'RA4-Table': Cfg(new_mix=0., formula='table', setassoc=False), 'RA-global': Cfg(new_mix=0., mode='global')}
MAIN = Cfg(new_mix=0.)


def env_info():
    commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', str(ROOT / 'src')], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    cpu = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip()
    mem = int(subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True).stdout.strip() or 0)
    return commit + ('+dirty' if dirty else ''), f'{cpu}, {mem // 2**30}GB, macOS'


def parse_workload(name):
    if name.startswith('zipf'):
        s, pool = name[4:].split('-')
        return float(s), pool
    if name.startswith('uniform'):
        return '', name.split('-')[1]
    return '', '全部' if name != '真实轨迹' else ''


def gama_original(ds, kib):
    f = OB / 'gama' / 'out' / ds / f'fp_{kib}.npy'
    info = OB / 'gama' / 'out' / ds / f'gama_{kib}.json'
    if not f.exists():
        return None
    meta = json.loads(info.read_text())
    from types import SimpleNamespace
    st = SimpleNamespace(fp_static=np.load(f), trees=meta['best_epoch'], model_bytes=meta['model_pickle_bytes'],
                         filter_bytes=int(meta['backup_bf_bits_target'] // 8), metadata_bytes=0, array_overhead_bytes=0,
                         used_bytes=meta['budget_bytes'])
    return dict(trees=meta['best_epoch'], frac=0., cache_reserved_bytes=0, cache_bytes=0, slots=0, structure=st,
                allocator='original Gama code (pickle accounting, FastPLBF_M N=50 k=5)')


def run(ds, budgets, queries, seeds, only=None):
    setup, scores, safe = E5.load(ds)
    commit, hw = env_info()
    pj = E5.C.CACHE / ds / 'preparation.json'
    if not pj.exists():          # COD/Caida caches are hard links to windows_research/cache (round 2 setup_sources)
        pj = ROOT.parent / 'cache' / ds / 'preparation.json'
    prep = json.loads(pj.read_text())
    specs = [('真实轨迹', None)] if ds.endswith('_flow') else E5.workload_specs(len(setup.h1q))
    if only:
        specs = [w for w in specs if w[0] in only]
    seeds = 1 if ds.endswith('_flow') else seeds
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    for kib in budgets:
        dest = out / f'rows_{ds}_{kib}.csv'
        done = set()
        if dest.exists():
            with dest.open(encoding='utf-8') as fh:
                done = {(r['workload'], int(r['seed'])) for r in csv.DictReader(fh)}
        t0 = time.perf_counter()
        cands = E5.candidates(setup, scores, kib)
        shared_build = time.perf_counter() - t0
        gama = E5.gama(cands)
        by = {(c['trees'], c['frac']): c for c in cands}
        statics = [('FastPLBF48', by.get((48, 0.))), ('Gama', gama), ('Gama(original)', gama_original(ds, kib)),
                   ('Gama+10%', by.get((gama['trees'], .1)))]
        for name, spec in specs:
            for seed in range(seeds):
                if (name, seed) in done:
                    continue
                start = time.perf_counter()
                base = E5.base_stream(setup, name, spec, seed, queries)
                n = len(base) // 4
                learn, base_tail = base[:n], base[n:]
                methods = [(m, c, dict(select_seconds=0., build_seconds=shared_build / len(cands), learn=0)) for m, c in statics if c]
                ts = time.perf_counter()
                grid, _ = E5.replay_best(cands, learn, setup, safe)
                methods.append(('LearnGrid', grid, dict(select_seconds=time.perf_counter() - ts,
                                                        build_seconds=shared_build / len(cands), learn=learn.nbytes)))
                ts = time.perf_counter()
                lm = RA.ra4.summarize(learn, True)
                lm_s = time.perf_counter() - ts
                extra = None
                if seed == 0:
                    extra = {'noGT': (RA.ra4.summarize(learn, False), Cfg(new_mix=0., gt=False)), 'mix0.5': (lm, Cfg(new_mix=.5))}
                c, info = RA.select(setup, scores, lm, kib, len(base_tail), MAIN, keep_table=seed == 0, extra_predictors=extra)
                info['select_seconds'] += lm_s
                info['learn'] = lm.state_bytes
                methods.append(('RA4', c, info))
                if seed < 3:
                    for vname, cfg in ABLATIONS.items():
                        ts = time.perf_counter()
                        lmv = lm if cfg.gt else RA.ra4.summarize(learn, False)
                        summ = time.perf_counter() - ts if not cfg.gt else lm_s
                        cv, iv = RA.select(setup, scores, lmv, kib, len(base_tail), cfg)
                        iv['select_seconds'] += summ
                        iv['learn'] = lmv.state_bytes
                        methods.append((vname, cv, iv))
                fp_oracle = ''
                if seed < 3:
                    orc = E5.oracle(cands, name, base_tail, seed, setup, safe)
                    fp_oracle = min(orc.values())
                rows = []
                zipf_s, pool = parse_workload(name)
                for method, cm, im in methods:
                    tail = E5.tail_for(cm, name, base_tail, seed)
                    r = E5.evaluate(cm, tail, setup, safe)
                    st = cm['structure']
                    assert st.used_bytes <= kib * 1024
                    rows.append(dict(dataset=ds, budget_kib=kib, workload=name, zipf_s=zipf_s, pool=pool, seed=seed,
                                     method=method, allocator=cm.get('allocator', 'FastPLBF_M DP N=1000 k=5'),
                                     trees=cm['trees'], cache_reserved_bytes=cm['cache_reserved_bytes'],
                                     cache_alloc_bytes=cm['cache_bytes'], model_bytes=st.model_bytes, bf_bytes=st.filter_bytes,
                                     metadata_bytes=st.metadata_bytes, overhead_bytes=st.array_overhead_bytes,
                                     total_bytes=st.used_bytes, fp_tail=r['fp'], fpr_tail=r['fp'] / len(tail),
                                     fp_oracle=fp_oracle, pred_fp=im.get('predicted_fp', ''),
                                     cache_hit_rate=round(r.get('cache_hit_rate', 0.), 6),
                                     t_train_s=round(prep['preparation_seconds'], 3), t_score_s='',
                                     t_select_s=round(im['select_seconds'], 4), t_build_s=round(im['build_seconds'], 4),
                                     learn_state_bytes=im['learn'],
                                     peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                     query_ns_mean='', query_ns_p50='', query_ns_p99='', backend_calls='',
                                     e2e_ms_mean='', e2e_ms_p99='', code_commit=commit, hardware=hw))
                if seed == 0 and 'table' in info:
                    e3 = []
                    for row in info['table']:
                        ccand = E5.build(setup, scores, row['trees'], kib, row['frac'], weights=row['weights'],
                                         cache_bytes=row['cache_bytes'], slots=row['slots'])
                        tail = E5.tail_for(ccand, name, base_tail, seed)
                        meas = E5.evaluate(ccand, tail, setup, safe)['fp']
                        e3.append(dict(trees=row['trees'], frac=row['frac'], pred=row['pred'],
                                       pred_noSA=row['pred_fullassoc'], **{f'pred_{k}': v for k, v in row['preds_other'].items()},
                                       measured=meas))
                    with (out / f'e3_{ds}_{kib}.jsonl').open('a', encoding='utf-8') as fh:
                        fh.write(json.dumps(dict(workload=name, seed=seed, candidates=e3), ensure_ascii=False) + '\n')
                new = not dest.exists()
                with dest.open('a', encoding='utf-8', newline='') as fh:
                    w = csv.DictWriter(fh, fieldnames=COLS)
                    if new:
                        w.writeheader()
                    w.writerows(rows)
                fps = {r['method']: r['fp_tail'] for r in rows}
                print(f'{ds} {kib}KiB {name} s{seed} {time.perf_counter()-start:.1f}s oracle={fp_oracle} '
                      + ' '.join(f'{k}={v}' for k, v in fps.items()), flush=True)
        print(f'COMPLETE {ds}/{kib}', flush=True)
        E5._TREE.clear()
        E5.R._GSETUPS.clear()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--budgets')
    p.add_argument('--queries', type=int, default=10_000_000)
    p.add_argument('--seeds', type=int, default=5)
    p.add_argument('--workloads')
    a = p.parse_args()
    run(a.dataset, [int(x) for x in a.budgets.split(',')] if a.budgets else E5.BUDGETS[a.dataset],
        a.queries, a.seeds, a.workloads.split(',') if a.workloads else None)
