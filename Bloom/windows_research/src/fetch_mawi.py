"""Acquire the predeclared fresh MAWI 2021 prefix, without examining model outcomes.

Only paths inside windows_research are written. The parser reads IP total length
directly rather than reconstructing length from tcpdump transport payload text.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://mawi.wide.ad.jp/mawi/samplepoint-F/2021/202104141400.pcap.gz'
LIMIT = 120_000_000
PACKETS = 10_000_000


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def download(seconds=600):
    data = ROOT / 'data'
    data.mkdir(exist_ok=True)
    target = data / 'mawi2021-prefix.pcap.gz'
    metadata = data / 'mawi2021-download.json'
    started = time.time()
    deadline = started + seconds
    events = []
    last_print = 0.0
    expected_total = None
    while time.time() < deadline and (not target.exists() or target.stat().st_size < LIMIT):
        offset = target.stat().st_size if target.exists() else 0
        remaining = max(1, deadline - time.time())
        try:
            with requests.get(URL, headers={'Range': f'bytes={offset}-{LIMIT-1}',
                                           'Accept-Encoding': 'identity'},
                              timeout=(min(20, remaining), min(20, remaining)), stream=True) as r:
                event = {'at_epoch': time.time(), 'offset': offset, 'status': r.status_code,
                         'content_range': r.headers.get('Content-Range'),
                         'content_length': r.headers.get('Content-Length')}
                events.append(event)
                print(json.dumps(event), flush=True)
                r.raise_for_status()
                if offset and r.status_code != 206:
                    raise RuntimeError('Server ignored resume Range; will not append duplicate bytes')
                if r.status_code == 206:
                    cr = r.headers.get('Content-Range', '')
                    if not cr.startswith(f'bytes {offset}-'):
                        raise RuntimeError(f'Unexpected Content-Range {cr}')
                    if '/' in cr and cr.split('/')[-1].isdigit():
                        expected_total = int(cr.split('/')[-1])
                elif r.headers.get('Content-Length', '').isdigit():
                    expected_total = int(r.headers['Content-Length'])
                with target.open('ab' if offset else 'wb') as f:
                    for chunk in r.iter_content(128 * 1024):
                        if not chunk:
                            continue
                        left = LIMIT - f.tell()
                        f.write(chunk[:left])
                        now = time.time()
                        if now - last_print > 10:
                            print(f'download bytes={f.tell():,}/{LIMIT:,} elapsed={now-started:.1f}s', flush=True)
                            last_print = now
                        if f.tell() >= LIMIT or now >= deadline:
                            break
            if expected_total is not None and target.stat().st_size >= min(LIMIT, expected_total):
                break
        except Exception as e:
            events.append({'at_epoch': time.time(), 'error': repr(e)})
            print(f'download retry: {e!r}', flush=True)
            if time.time() < deadline:
                time.sleep(min(3, max(0, deadline-time.time())))
    size = target.stat().st_size if target.exists() else 0
    result = {'url': URL, 'predeclared_compressed_prefix_bytes': LIMIT,
              'predeclared_max_packet_records': PACKETS,
              'bytes_downloaded': size, 'expected_source_bytes': expected_total,
              'prefix_complete': size >= LIMIT,
              'elapsed_s': time.time()-started, 'events': events,
              'sha256': sha(target) if target.exists() else None,
              'no_model_training_or_evaluation_performed': True}
    save(metadata, result)
    print(json.dumps({k:v for k,v in result.items() if k != 'events'}, indent=2), flush=True)
    return result


def ip_offset(packet, linktype):
    if linktype == 1:  # Ethernet, including 802.1Q and provider VLAN nesting
        if len(packet) < 14:
            return None
        off, ethertype = 14, struct.unpack('!H', packet[12:14])[0]
        while ethertype in (0x8100, 0x88A8, 0x9100):
            if len(packet) < off + 4:
                return None
            ethertype = struct.unpack('!H', packet[off+2:off+4])[0]
            off += 4
        return off if ethertype in (0x0800, 0x86DD) else None
    if linktype in (12, 14, 101, 228, 229):
        return 0
    if linktype == 0:  # BSD loopback
        return 4
    if linktype == 113:  # Linux cooked v1
        return 16
    if linktype == 276:  # Linux cooked v2
        return 20
    raise ValueError(f'Unsupported PCAP linktype {linktype}')


def parse():
    data = ROOT / 'data'
    source = data / 'mawi2021-prefix.pcap.gz'
    target = data / 'mawi2021.csv'
    metadata = data / 'mawi2021-source.json'
    records = retained = ipv4 = ipv6 = non_tcp_udp = short_packets = 0
    truncated_tail = False
    error = None
    linktype = None
    started = time.time()
    try:
        with gzip.open(source, 'rb') as f, target.open('w', newline='', encoding='utf-8') as out:
            header = f.read(24)
            if len(header) != 24:
                raise ValueError('Missing PCAP global header')
            magics = {b'\xd4\xc3\xb2\xa1': '<', b'\xa1\xb2\xc3\xd4': '>',
                      b'\x4d\x3c\xb2\xa1': '<', b'\xa1\xb2\x3c\x4d': '>'}
            if header[:4] not in magics:
                raise ValueError(f'Unsupported PCAP magic {header[:4].hex()}')
            endian = magics[header[:4]]
            linktype = struct.unpack(endian+'I', header[20:24])[0]
            print(f'PCAP linktype={linktype} endian={endian}', flush=True)
            writer = csv.writer(out)
            writer.writerow(['No.', 'Source', 'Destination', 'Length', 'Label'])
            for number in range(PACKETS):
                rh = f.read(16)
                if not rh:
                    break
                if len(rh) < 16:
                    truncated_tail = True
                    break
                _, _, captured, original = struct.unpack(endian+'IIII', rh)
                if captured > 16_777_216:
                    raise ValueError(f'Invalid packet captured length {captured}')
                packet = f.read(captured)
                if len(packet) < captured:
                    truncated_tail = True
                    break
                records += 1
                off = ip_offset(packet, linktype)
                if off is None or len(packet) <= off:
                    continue
                version = packet[off] >> 4
                if version == 4:
                    if len(packet) < off+20:
                        short_packets += 1
                        continue
                    proto = packet[off+9]
                    length = struct.unpack('!H', packet[off+2:off+4])[0]
                    src = int.from_bytes(packet[off+12:off+16], 'big')
                    dst = int.from_bytes(packet[off+16:off+20], 'big')
                    ipv4 += 1
                elif version == 6:
                    if len(packet) < off+40:
                        short_packets += 1
                        continue
                    proto = packet[off+6]
                    length = 40 + struct.unpack('!H', packet[off+4:off+6])[0]
                    src = int.from_bytes(packet[off+8:off+12], 'big')
                    dst = int.from_bytes(packet[off+24:off+28], 'big')
                    ipv6 += 1
                    # Follow basic IPv6 extension-header chain when captured.
                    pos = off+40
                    while proto in (0, 43, 44, 51, 60):
                        if len(packet) < pos+2:
                            proto = -1
                            break
                        next_proto = packet[pos]
                        step = 8 if proto == 44 else ((packet[pos+1]+2)*4 if proto == 51 else (packet[pos+1]+1)*8)
                        pos += step
                        proto = next_proto
                else:
                    continue
                if proto not in (6, 17):
                    non_tcp_udp += 1
                    continue
                writer.writerow([number+1, src, dst, length, int(proto == 17)])
                retained += 1
                if records % 1_000_000 == 0:
                    print(f'parsed records={records:,} retained={retained:,}', flush=True)
    except (EOFError, gzip.BadGzipFile) as e:
        truncated_tail = True
        error = repr(e)
    result = {'url': URL, 'input': str(source), 'input_bytes': source.stat().st_size,
              'input_sha256': sha(source), 'csv': str(target),
              'csv_sha256': sha(target) if target.exists() else None,
              'predeclared_max_packet_records': PACKETS, 'packet_records_read': records,
              'retained_tcp_udp_packets': retained, 'ipv4_headers': ipv4, 'ipv6_headers': ipv6,
              'non_tcp_udp': non_tcp_udp, 'short_packets': short_packets,
              'truncated_compressed_tail': truncated_tail, 'tail_error': error,
              'pcap_linktype': linktype, 'elapsed_s': time.time()-started,
              'length_semantics': 'IPv4 total-length header; IPv6 fixed40+payload-length header',
              'address_semantics': 'IPv4 network-byte-order uint32; IPv6 upper32bits',
              'protocol_membership': 'UDP flows are members, TCP flows are negatives',
              'difference_from_original': 'Direct IP lengths instead of tcpdump payload+fixed transport header approximation; packet prefix unchanged.',
              'no_model_training_or_evaluation_performed': True}
    save(metadata, result)
    print(json.dumps(result, indent=2), flush=True)
    return result


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['download', 'parse', 'all'])
    ap.add_argument('--seconds', type=float, default=600)
    args = ap.parse_args()
    if args.command in ('download','all'):
        download(args.seconds)
    if args.command in ('parse','all'):
        parse()
