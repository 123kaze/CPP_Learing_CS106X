"""Exact RA6 equivalence and regression checks; no timing thresholds."""
import math

PREFIXES = {str(n) for n in (1, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160, 200)}
QUERY_FIELDS = ('queries', 'negatives', 'fp', 'fn', 'batch', 'cache_hits', 'model_calls')
QUERY_NAMES = ('negative_tail', 'mixed_batch', 'mixed_scalar')


def healthy(r):
    assert r['status'] == 'ok' and r['exit_code'] == 0
    assert r['threads'] == 1 and r['member_false_negatives'] == 0
    assert math.isfinite(r['train_to_ready_s']) and r['train_to_ready_s'] > 0
    assert r['train_to_ready_s'] < r['process_wall_s']
    assert r['train_plus_tail_s'] == r['train_to_ready_s'] + r['queries']['negative_tail']['seconds']
    assert set(r['queries']) == set(QUERY_NAMES)
    for name in QUERY_NAMES:
        q = r['queries'][name]
        assert q['fn'] == 0 and 0 <= q['fp'] <= q['negatives'] <= q['queries']
        assert math.isfinite(q['seconds']) and q['seconds'] > 0


def check_pair(loop, leaf):
    for r in (loop, leaf):
        healthy(r)
        assert r['main_table_check']['equal'] is True
        assert set(r['score_sha256']) == PREFIXES
        assert r['used_bytes'] <= r['budget_kib'] * 1024
    assert loop['scoring'] == 'loop' and leaf['scoring'] == 'leaf'
    for key in ('dataset', 'budget_kib', 'rep', 'fixture', 'model_sha256', 'score_sha256',
                'trees', 'cache_bytes', 'used_bytes', 'member_index_bytes', 'bf_payload_sha256',
                'static_flags_sha256', 'executable_model_sha256', 'native_pool_flags_sha256',
                'native_pool_fp', 'native_pool_queries', 'main_table_check'):
        assert loop[key] == leaf[key], key
    for key in ('trees', 'frac', 'predicted_fp', 'ra4_rank', 'candidates', 'built'):
        assert loop['shortlist'][key] == leaf['shortlist'][key], ('shortlist', key)
    for name in QUERY_NAMES:
        for key in QUERY_FIELDS:
            assert loop['queries'][name][key] == leaf['queries'][name][key], (name, key)
    return dict(dataset=loop['dataset'], budget_kib=loop['budget_kib'], rep=loop['rep'],
                bit_exact_prefixes=14, identical_config=True, identical_native_fp=True)


def check_archive(current, archived, method):
    healthy(current)
    assert archived['status'] == 'ok'
    fields = ['dataset', 'budget_kib', 'fixture', 'trees', 'member_index_bytes', 'member_false_negatives']
    fields += (['cache_bytes', 'used_bytes'] if method != 'gama' else
               ['model_pickle_bytes', 'bf_target_bits', 'bf_logical_bits', 'bf_array_payload_bytes', 'evaluated_epochs'])
    for key in fields:
        assert current[key] == archived[key], ('round7', method, key)
    for name in QUERY_NAMES:
        for key in QUERY_FIELDS:
            assert current['queries'][name][key] == archived['queries'][name][key], ('round7', method, name, key)
