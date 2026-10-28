"""把 MAWI（WIDE 骨干网，samplepoint-F）tcpdump 文本转成与 HTTYF 的 caida.csv 同格式的 CSV。

输入：tcpdump -nn -q -tt 的输出（每行一个包）。只保留 TCP / UDP（IPv4 与 IPv6）。
输出列：No., Time, Source, Destination, Label（UDP=1, TCP=0）, Length。
Length 换算成 IP 包总长，与 Caida 同口径：tcpdump -q 给的是净载荷长度（TCP 纯 ACK 为 0，几乎等于直接泄露协议），
这里加上最小头部：IPv4 的 TCP +40、UDP +28；IPv6 的 TCP +60、UDP +48（不计 TCP 选项）。
Source/Destination 为地址的整数值（IPv6 取高 32 位），与 Caida 的数值地址同口径；MAWI 的地址已做前缀保持匿名化。

用法：python src/prepare_mawi.py external/mawi/mawi2020.txt external/mawi/mawi2020.csv
"""

import ipaddress
import sys

import numpy as np
import pandas as pd


PATTERN = r"^(?P<t>\d+\.\d+) (?P<ipv>IP6?) (?P<src>\S+) > (?P<dst>\S+): (?P<proto>tcp|UDP)(?:, length)? (?P<len>\d+)"


def addr_int(hostport):
    host = hostport.rsplit(".", 1)[0]          # 去掉端口
    ip = ipaddress.ip_address(host)
    return int(ip) if ip.version == 4 else int(ip) >> 96


def main(src, dst):
    lines = pd.read_csv(src, sep="\x01", header=None, names=["line"], dtype=str, engine="c").line
    m = lines.str.extract(PATTERN)
    m = m.dropna()
    hosts = pd.unique(pd.concat([m.src, m.dst]))
    lookup = {h: addr_int(h) for h in hosts}
    out = pd.DataFrame({
        "No.": np.arange(1, len(m) + 1),
        "Time": m.t.astype(float).to_numpy(),
        "Source": m.src.map(lookup).to_numpy(),
        "Destination": m.dst.map(lookup).to_numpy(),
        "Label": (m.proto == "UDP").astype(int).to_numpy(),
        "Length": (m.len.astype(int) + np.where(m.proto == "tcp", 40, 28) + np.where(m.ipv == "IP6", 20, 0)).to_numpy(),
    })
    out.to_csv(dst, index=False)
    print(f"{src}: {len(lines):,} 行 → {len(out):,} 个 TCP/UDP 包（UDP {out.Label.sum():,}）")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
