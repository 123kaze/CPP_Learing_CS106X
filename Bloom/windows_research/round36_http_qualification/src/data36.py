"""Aggregate HTTP traffic only: discard client identities and never publish raw keys."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_v] = '1'
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'round27_http_real/src'))
from data27 import lexical, FEATURES
sys.path.insert(0, str(ROOT / 'src'))
from fetch36 import save, sha
import array
from collections import Counter
from datetime import datetime, timezone, timedelta
import gzip
import hashlib
import re
import resource
import time
import numpy as np

ROW = re.compile(rb'^\S+\s+(.*?)\s+"([^"\r\n]*)"\s+(\d{3})\s+(\S+)(?:\s.*)?$')
CLF = re.compile(rb'\[(\d{1,2})/([A-Za-z]{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})(?:\s+([+-]\d{4}))?\]')
CTIME = re.compile(rb'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Za-z]{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\s+(\d{4})')
MONTHS = {m.encode(): i+1 for i, m in enumerate(('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'))}


def decode_line(line):
    """Return only time, target, status. The originating host is never retained."""
    m = ROW.match(line.rstrip(b'\r\n'))
    if not m:
        return None, 'malformed_record'
    prefix, request, status = m.group(1), m.group(2), int(m.group(3))
    parts = request.split()
    if not parts or parts[0] != b'GET':
        return None, 'non_GET'
    if len(parts) not in (2, 3) or (len(parts) == 3 and not parts[2].startswith(b'HTTP/')):
        return None, 'malformed_GET_request'
    match = CLF.search(prefix)
    try:
        if match:
            day, month, year, hour, minute, second, zone = match.groups()
            zone = zone or b'-0400'
            offset = (1 if zone[:1] == b'+' else -1) * (int(zone[1:3])*60+int(zone[3:]))
            kind = 'CLF'
        else:
            match = CTIME.search(prefix)
            if not match:
                return None, 'unknown_GET_timestamp'
            month, day, hour, minute, second, year = match.groups()
            offset = -240
            kind = 'ctime_documented_minus0400'
        stamp = datetime(int(year), MONTHS[month], int(day), int(hour), int(minute), int(second),
                         tzinfo=timezone(timedelta(minutes=offset)))
    except (KeyError, ValueError):
        return None, 'invalid_GET_timestamp'
    return (stamp, parts[1], status, kind), None


def parse(sources, destination, name):
    destination = Path(destination)
    assert not destination.exists(), 'Refuse prepared-data overwrite'
    start = time.perf_counter()
    keys = {}; targets = []; flags = []; first = []; first_success = []; first_absent = []
    record_key = array.array('q'); record_status = array.array('B'); record_order = array.array('q')
    total = parsed = reversals = 0
    counts = Counter(); skipped = Counter(); formats = Counter(); months = {}
    first_stamp = last_stamp = previous = minimum = maximum = None
    files = []
    for source in map(Path, sources):
        local_lines = local_parsed = 0
        local_first = local_last = None
        with gzip.open(source, 'rb') as f:
            while True:
                line = f.readline(65537)
                if not line:
                    break
                assert len(line) <= 65536, 'Untrusted record exceeds 64 KiB limit'
                total += 1; local_lines += 1
                item, reason = decode_line(line)
                if reason:
                    skipped[reason] += 1
                    continue
                stamp, target, status, kind = item
                order = parsed; parsed += 1; local_parsed += 1
                formats[kind] += 1; counts[status] += 1
                month = f'{stamp.year:04d}-{stamp.month:02d}'
                months.setdefault(month, Counter())[status] += 1
                if previous is not None and stamp < previous:
                    reversals += 1
                previous = last_stamp = local_last = stamp
                if first_stamp is None: first_stamp = stamp
                if local_first is None: local_first = stamp
                minimum = stamp if minimum is None else min(minimum, stamp)
                maximum = stamp if maximum is None else max(maximum, stamp)
                if status not in (200, 304, 404):
                    continue
                k = keys.get(target)
                if k is None:
                    k = len(targets); keys[target] = k; targets.append(target)
                    flags.append(0); first.append(order); first_success.append(-1); first_absent.append(-1)
                flag = 2 if status == 404 else 1
                flags[k] |= flag
                seen = first_absent if flag == 2 else first_success
                if seen[k] == -1: seen[k] = order
                record_key.append(k); record_status.append(flag); record_order.append(order)
        files.append(dict(file=source.name, sha256=sha(source), lines=local_lines, parsed_GET=local_parsed,
                          first_timestamp=local_first.isoformat() if local_first else None,
                          last_timestamp=local_last.isoformat() if local_last else None))
    assert parsed > 0, 'No parsed GET requests'
    flag = np.asarray(flags, np.uint8); keep = flag != 3; idx = np.flatnonzero(keep)
    mapping = np.full(len(flags), -1, np.int64); mapping[idx] = np.arange(len(idx))
    rk = np.asarray(record_key, np.int64); ro = np.asarray(record_order, np.int64); rs = np.asarray(record_status, np.uint8)
    good = keep[rk]; boundary = parsed//4
    ids = np.array([int.from_bytes(hashlib.sha256(targets[i]).digest()[:8], 'little') for i in idx], np.uint64)
    assert len(np.unique(ids)) == len(ids), 'Finite resource ID collision: stop, do not merge'
    X = np.asarray([lexical(targets[i]) for i in idx], np.float32).reshape((-1, len(FEATURES)))
    y = flag[idx] == 1
    trace = mapping[rk[good]]; order = ro[good]
    fsuccess = np.asarray(first_success, np.int64); fabsent = np.asarray(first_absent, np.int64)
    conflicting = flag == 3
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez(destination, ids=ids, X=X, y=y, trace=trace, order=order, first=np.asarray(first, np.int64)[idx],
             boundary=np.int64(boundary), features=np.asarray(FEATURES))
    def window(mask):
        seq = trace[mask & ~y[trace]]
        freq = np.bincount(seq, minlength=len(ids))
        n = len(seq); distinct = int((freq > 0).sum())
        return dict(requests=n, distinct=distinct, singleton_keys=int((freq == 1).sum()),
                    repeat_fraction=1-distinct/n if n else None)
    overlaps = X.view(np.dtype((np.void, X.dtype.itemsize*len(FEATURES)))).ravel()
    overlap = np.intersect1d(overlaps[y], overlaps[~y])
    meta = dict(status='complete', dataset=name, lines=total, parsed_GET=parsed, status_counts=dict(counts),
                skipped=dict(skipped), timestamp_formats=dict(formats), files=files,
                first_timestamp=first_stamp.isoformat(), last_timestamp=last_stamp.isoformat(),
                minimum_timestamp=minimum.isoformat(), maximum_timestamp=maximum.isoformat(),
                recorded_order_time_reversals=reversals, monthly_status_counts={k:dict(v) for k,v in sorted(months.items())},
                members=int(y.sum()), negative_keys=int((~y).sum()), stable_keys=len(ids), conflicting_keys=int(conflicting.sum()),
                conflicting_success_requests=int(((~good)&(rs==1)).sum()), conflicting_404_requests=int(((~good)&(rs==2)).sum()),
                development_404_then_future_success_keys=int((conflicting&(fabsent>=0)&(fabsent<boundary)&(fsuccess>=boundary)).sum()),
                development_success_then_future_404_keys=int((conflicting&(fsuccess>=0)&(fsuccess<boundary)&(fabsent>=boundary)).sum()),
                retained_success_requests=int((good&(rs==1)).sum()), retained_404_requests=int((good&(rs==2)).sum()),
                retained_404_fraction=float((good&(rs==2)).sum()/counts[404]) if counts[404] else 0.,
                development=window(order<boundary), tail=window(order>=boundary), boundary_GET_ordinal=boundary,
                exact_feature_overlap_vectors=len(overlap), negative_keys_sharing_features_with_members=int(np.isin(overlaps[~y],overlaps[y]).sum()),
                features=FEATURES, prepared_sha256=sha(destination), parse_feature_and_write_s=time.perf_counter()-start,
                peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
                construction='retrospective stable subset; full-trace catalog and conflict exclusions; original recorded order retained')
    save(destination.with_suffix('.json'), meta)
    print('PARSED', name, 'members', meta['members'], 'negative_keys', meta['negative_keys'], '404', meta['retained_404_requests'], flush=True)
    return meta
