"""Exact semantic equivalence checks for a paired loop/leaf construction."""
import argparse
import json
from pathlib import Path


def check(loop,leaf):
    for r in (loop,leaf):
        assert r['status']=='ok'
        assert r['member_false_negatives']==0
    assert loop['scoring']=='loop' and leaf['scoring']=='leaf'
    for key in ('dataset','budget_kib','model_sha256','score_sha256','member_index_bytes'):
        assert loop[key]==leaf[key],key
    for name in ('once','zipf'):
        a,b=loop['workloads'][name],leaf['workloads'][name]
        for key in ('trees','frac','cache_bytes','used_bytes','fp','fn','queries','negatives',
                    'static_flags_sha256','bf_payload_sha256'):
            assert a[key]==b[key],(name,key,a[key],b[key])
        for key in ('trees','frac','predicted_fp','ra4_rank','candidates','built'):
            assert a['selection'][key]==b['selection'][key],(name,'selection',key)
        if name=='once':
            for key in ('fp','fn','queries','negatives'):
                assert a['pool'][key]==b['pool'][key],(name,'pool',key)
    return dict(dataset=loop['dataset'],budget_kib=loop['budget_kib'],
                bit_exact_prefixes=len(loop['score_sha256']),identical_configs=2,
                identical_filter_payloads=True,identical_native_fp=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('loop',type=Path);p.add_argument('leaf',type=Path);a=p.parse_args()
    print(json.dumps(check(json.loads(a.loop.read_text()),json.loads(a.leaf.read_text())),indent=2))
