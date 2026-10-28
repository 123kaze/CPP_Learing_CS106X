"""Known-packet parser tests; no real validation-set models are evaluated."""
import csv
import gzip
import json
from pathlib import Path
import struct
import tempfile
import fetch_mawi as F

ROOT = Path(__file__).resolve().parents[1]


def ipv4(proto, length):
    h = bytearray(20)
    h[0] = 0x45
    h[2:4] = struct.pack('!H', length)
    h[9] = proto
    h[12:16] = bytes([1, 2, 3, 4])
    h[16:20] = bytes([5, 6, 7, 8])
    return bytes(h)


def main():
    (ROOT / 'tmp').mkdir(exist_ok=True)
    v6 = bytearray(40)
    v6[0] = 0x60
    v6[4:6] = struct.pack('!H', 8)
    v6[6] = 17
    v6[8:12] = bytes([0x20, 0x01, 0x0d, 0xb8])
    v6[24:28] = bytes([0x20, 0x01, 0x0d, 0xb9])
    packets = [bytes(12)+bytes.fromhex('0800')+ipv4(17, 28),
               bytes(12)+bytes.fromhex('0800')+ipv4(6, 60),
               bytes(12)+bytes.fromhex('810000010800')+ipv4(6, 40),
               bytes(12)+bytes.fromhex('86dd')+bytes(v6)]
    header = bytes.fromhex('d4c3b2a1') + struct.pack('<HHIIII', 2, 4, 0, 0, 65535, 1)
    pcap = header+b''.join(struct.pack('<IIII', 1, 0, len(p), len(p))+p for p in packets)
    old_root = F.ROOT
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
        F.ROOT = Path(directory)
        data = F.ROOT / 'data'
        data.mkdir()
        source = data / 'mawi2021-prefix.pcap.gz'
        source.write_bytes(gzip.compress(pcap))
        result = F.parse()
        with (data / 'mawi2021.csv').open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        assert result['packet_records_read'] == 4
        assert result['retained_tcp_udp_packets'] == 4
        assert not result['truncated_compressed_tail']
        assert [int(r['Length']) for r in rows] == [28, 60, 40, 48]
        assert [int(r['Label']) for r in rows] == [1, 0, 0, 1]
        assert int(rows[0]['Source']) == 0x01020304
        assert int(rows[3]['Source']) == 0x20010db8
        source.write_bytes(gzip.compress(pcap)[:-8])
        truncated = F.parse()
        assert truncated['truncated_compressed_tail']
        assert truncated['packet_records_read'] == 4
        assert F.ip_offset(packets[2], 1) == 18
        assert F.ip_offset(bytes(14), 1) is None
    F.ROOT = old_root
    out = {'passed': True, 'tests': ['IPv4 UDP and exact header length',
           'TCP total length including options', 'Ethernet VLAN', 'IPv6 UDP upper32 address',
           'truncated gzip footer retains complete records', 'non-IP Ethernet skipped']}
    (ROOT / 'evidence/mawi-parser-tests.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
