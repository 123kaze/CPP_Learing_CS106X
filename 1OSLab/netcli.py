#!/usr/bin/env python3
"""
netcli.py — 计算机网络学习 CLI 工具

一个用 Python 标准库写的网络调试客户端，
每个命令帮你理解一个网络协议的核心概念。

用法:
  python3 netcli.py <命令> [参数]

命令列表:
  connect  <host> <port>     TCP 三次握手 + 收发数据
  http     <url>             HTTP 协议: 请求行/头/体
  https    <url>             TLS 握手 + HTTPS
  dns      <domain>          DNS 解析全过程
  ifaces                    查看本机网卡和 IP
  listen   <port>           启动简易 TCP 服务端
  proxy    <port> <upstream> HTTP 正向代理 (理解中间人)

示例:
  python3 netcli.py connect example.com 80
  python3 netcli.py http http://httpbin.org/get
  python3 netcli.py dns www.baidu.com
  python3 netcli.py ifaces
  python3 netcli.py listen 9999
"""

import sys
import socket
import struct
import ssl
import ipaddress
import argparse
import re
from collections import namedtuple


# ═══════════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════════

def hr(title):
    """打印分隔标题"""
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def info(label, value):
    """打印键值对"""
    print(f"  {label:20s} : {value}")


# ═══════════════════════════════════════════════════════════════════════
# 1. connect — TCP 三次握手 + 收发数据
# ═══════════════════════════════════════════════════════════════════════
#
# TCP 建立连接需要三次握手:
#
#   客户端                          服务端
#   ───────                        ──────
#   socket()                       socket() + bind() + listen()
#     │                               │
#     │ ──── SYN (seq=x) ──────────→  │  客户端: SYN_SENT
#     │                               │  服务端: SYN_RCVD (放入 SYN 队列)
#     │                               │
#     │ ←── SYN+ACK (seq=y,ack=x+1)─ │  客户端: ESTABLISHED (进入 ACCEPT 队列)
#     │                               │  服务端: 仍在 SYN_RCVD
#     │                               │
#     │ ──── ACK (ack=y+1) ────────→  │  客户端: ESTABLISHED
#     │                               │  服务端: ESTABLISHED → 移到 ACCEPT 队列
#     │                               │
#   connect() 返回                  accept() 返回
#
# connect() 在内核里做的事:
#   1. 给 socket 分配一个临时端口 (ephemeral port, 范围 32768-60999)
#   2. 把 socket 状态从 CLOSED 改为 SYN_SENT
#   3. 构造 SYN 包发给对端
#   4. 等待 SYN+ACK, 收到后发 ACK
#   5. 状态变为 ESTABLISHED, connect() 返回
# ======================================================================

def cmd_connect(args):
    """TCP connect — 完整展示三次握手到数据传输"""
    host, port = args.host, args.port

    hr(f"TCP Connect: {host}:{port}")

    # ── 步骤 1: DNS 解析 ──
    # getaddrinfo() 把域名转成 IP, 同时查了 DNS。
    # 返回一个列表, 每个元素是 (family, type, proto, canonname, sockaddr)
    # family: AF_INET(IPv4) 或 AF_INET6(IPv6)
    # sockaddr: (ip, port) 二元组
    #
    # 为什么不用 gethostbyname()?
    #   gethostbyname 只返回 IPv4, 且线程不安全。
    #   getaddrinfo 是现代做法, 支持 IPv4/IPv6, 支持指定 socktype。
    print("\n[1/4] DNS 解析...")
    addrinfo_list = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    for ai in addrinfo_list:
        family, stype, proto, canon, sockaddr = ai
        family_name = {socket.AF_INET: "IPv4", socket.AF_INET6: "IPv6"}.get(family, f"family={family}")
        info("解析结果", f"{sockaddr[0]}:{sockaddr[1]} ({family_name})")

    # ── 步骤 2: socket() — 创建 socket ──
    # 内核分配 struct socket (状态 SS_UNCONNECTED) + struct inet_sock
    print("\n[2/4] socket() — 创建 socket")
    sock = socket.socket(addrinfo_list[0][0], socket.SOCK_STREAM, 0)
    info("fd", sock.fileno())
    info("内核状态", "SS_UNCONNECTED (struct socket 已分配, 无地址绑定)")

    # ── 步骤 3: connect() — 三次握手 ──
    # connect() 触发三次握手:
    #   1. 内核分配临时端口 → 填入 inet_sock.sport
    #   2. 发送 SYN → 状态变 SYN_SENT
    #   3. 收到 SYN+ACK → 发 ACK → 状态变 ESTABLISHED → connect() 返回
    print("\n[3/4] connect() — 发起 TCP 三次握手...")
    try:
        sock.connect(addrinfo_list[0][4])  # (ip, port)
    except ConnectionRefusedError:
        print("  ❌ 连接被拒绝 (RST) — 可能服务端端口未开")
        return
    except socket.timeout:
        print("  ❌ 连接超时 — 可能防火墙丢弃了 SYN 包")
        return

    # connect() 成功后, 四元组就确定了
    local_addr  = sock.getsockname()  # (本机IP, 本机端口)
    remote_addr = sock.getpeername()  # (对端IP, 对端端口)
    info("四元组", f"{local_addr[0]}:{local_addr[1]} → {remote_addr[0]}:{remote_addr[1]}")
    info("内核状态", "ESTABLISHED (三次握手完成)")

    # ── 步骤 4: send/recv — 收发数据 ──

    # 如果连接的是 HTTP 端口, 自动发一个 GET 请求
    if port in (80, 8080) and args.data is None and not args.interactive:
        args.data = f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"

    if args.interactive:
        # ═════════════════════════════════════════════════════════════
        # 交互模式: 用户打字 → 发送 → 接收回显 → 继续等待输入
        #
        # 不发 shutdown(SHUT_WR), 连接保持全双工。
        # 适合跟 echo server 聊天。
        # ═════════════════════════════════════════════════════════════
        print("\n[4/5] 交互模式 — 打字发送, Ctrl+D 退出")
        print("=" * 50)
        try:
            while True:
                line = input(">>> ")
                sock.sendall((line + "\n").encode())
                # 读回显 (设超时避免永久阻塞)
                sock.settimeout(1.0)
                try:
                    reply = sock.recv(4096)
                    if reply:
                        print(f"    {reply.decode('utf-8', errors='replace').rstrip()}")
                    else:
                        print("    (对端关闭)")
                        break
                except socket.timeout:
                    pass  # 没回显就算了, 继续
                sock.settimeout(None)
        except EOFError:
            # Ctrl+D → 半关闭写端
            print("\n\n  shutdown(SHUT_WR) → 发送 FIN, 告诉对端\"我不发了\"")
            print("  (TCP 半关闭: 还能收, 不能发)")
            sock.shutdown(socket.SHUT_WR)
            # 收完剩余的
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    print(f"  ← {chunk.decode('utf-8', errors='replace').rstrip()}")
                except Exception:
                    break
        except KeyboardInterrupt:
            print("\n  中断")
    else:
        # ═════════════════════════════════════════════════════════════
        # 单次模式: 发送 → shutdown(SHUT_WR) → 收完所有响应
        #
        # 为什么要 shutdown(SHUT_WR)?
        #
        #   TCP 是字节流, 没有"消息边界"。你发完数据后,
        #   对端不知道你"说完了"。Echo Server 的 read() 会一直
        #   阻塞等下一批数据。你也在 recv() 里等对端的回显/关闭。
        #   → 双方都在等 → 死锁。
        #
        #   shutdown(SHUT_WR) 告诉内核:
        #     "关闭写端, 发送 FIN 给对端。读端保持打开。"
        #   这叫 TCP 半关闭 (Half-Close)。
        #
        #   之后:
        #     对端 read() 返回 0 (收到 FIN) → 对端 close()
        #     → 我们的 recv() 返回 0 (收到对端的 FIN) → 结束
        #
        #   状态变化:
        #     客户端: ESTABLISHED → FIN_WAIT_1 → FIN_WAIT_2 → TIME_WAIT
        #     服务端: ESTABLISHED → CLOSE_WAIT → LAST_ACK → CLOSED
        # ═════════════════════════════════════════════════════════════
        print("\n[4/5] send() — 发送数据")

        if args.timeout:
            sock.settimeout(args.timeout)

        if args.data:
            data = args.data.encode() if isinstance(args.data, str) else args.data
            print(f"  → 发送 {len(data)} 字节")
            sock.sendall(data)
            # sendall() vs send():
            #   send()  可能只发一部分 (发送缓冲区满时返回实际发送字节数)
            #   sendall() 内部循环 send(), 保证全部发完或报错

        # ===== 关键: 半关闭写端 =====
        print(f"\n[5/5] shutdown(SHUT_WR) + recv()")
        print(f"  → shutdown(SHUT_WR): 发送 FIN, 告诉对端\"我发完了\"")
        print(f"  → 客户端状态: ESTABLISHED → FIN_WAIT_1")
        print(f"  → 对端 read() 将返回 0 (意味着\"收到EOF\")")
        print(f"  → 对端 close() → 我们收到 FIN → recv() 返回 0\n")
        sock.shutdown(socket.SHUT_WR)
        # shutdown(fd, SHUT_WR) vs close(fd):
        #   shutdown(SHUT_WR) — 只关写端, 还能读。发送 FIN, 进入半关闭。
        #   close(fd)          — 读写全关, 立即返回。但如果有数据没读完, 数据丢失。

        # 接收响应 — 现在不会死锁了, 因为对端会收到 FIN 然后关闭
        print("  ← 等待接收...")
        total = 0
        while True:
            try:
                chunk = sock.recv(4096)
            except ConnectionResetError:
                print("  ⚠️  连接被对端重置 (RST)")
                break
            except socket.timeout:
                print(f"  ⚠️  recv 超时 (共收 {total} 字节)")
                break
            if not chunk:
                print(f"  ← 收到 FIN (对端关闭), 共接收 {total} 字节")
                break
            total += len(chunk)
            if total <= 500:
                try:
                    print(f"  ← recv {len(chunk)}B: {chunk.decode('utf-8', errors='replace')[:200]}")
                except Exception:
                    print(f"  ← recv {len(chunk)}B (binary)")
            elif total - len(chunk) <= 500:
                print(f"  ← ... (省略中间 {total - 500}B) ...")
                try:
                    print(f"  ← recv {len(chunk)}B: {chunk.decode('utf-8', errors='replace')[:200]}")
                except Exception:
                    print(f"  ← recv {len(chunk)}B (binary)")

    # close() → 四次挥手
    sock.close()
    print(f"\n  close() → 四次挥手完成 → TIME_WAIT(主动关闭端, 2MSL≈60s)")


# ═══════════════════════════════════════════════════════════════════════
# 2. http — HTTP 协议
# ═══════════════════════════════════════════════════════════════════════
#
# HTTP/1.1 请求格式:
#
#   GET /path HTTP/1.1\r\n          ← 请求行: 方法 URI 版本
#   Host: example.com\r\n            ← 头部 (Header)
#   User-Agent: netcli\r\n
#   \r\n                             ← 空行 (头部结束)
#   (body)                           ← 可选, GET 通常没有
#
# HTTP/1.1 响应格式:
#
#   HTTP/1.1 200 OK\r\n              ← 状态行: 版本 状态码 原因短语
#   Content-Type: text/html\r\n      ← 响应头
#   Content-Length: 1234\r\n
#   \r\n                             ← 空行
#   <html>...</html>                 ← 响应体
#
# HTTP 基于 TCP: 先三次握手 → 发 HTTP 文本 → 收 HTTP 文本 → 四次挥手
# ======================================================================

def parse_url(url):
    """手动解析 URL: scheme://host[:port]/path"""
    m = re.match(r'^(https?)://([^/:]+)(?::(\d+))?(/.*)?$', url)
    if not m:
        m = re.match(r'^([^/:]+)(?::(\d+))?(/.*)?$', url)
        if not m:
            raise ValueError(f"无法解析 URL: {url}")
        scheme, host, port, path = 'http', m.group(1), m.group(2), m.group(3)
    else:
        scheme, host, port, path = m.group(1), m.group(2), m.group(3), m.group(4)
    if port is None:
        port = 443 if scheme == 'https' else 80
    else:
        port = int(port)
    if path is None:
        path = '/'
    return scheme, host, port, path


def cmd_http(args):
    """HTTP GET — 展示完整的 HTTP 请求/响应"""
    url = args.url
    scheme, host, port, path = parse_url(url)

    hr(f"HTTP GET {url}")
    info("解析结果", f"scheme={scheme}, host={host}, port={port}, path={path}")

    # ── 步骤 1: TCP 连接 ──
    print(f"\n[1/3] TCP connect → {host}:{port}")
    sock = socket.create_connection((host, port), timeout=10)
    info("TCP 连接", "ESTABLISHED")

    # ── 步骤 2: 构造并发送 HTTP 请求 ──
    #
    # HTTP 协议的核心就是一个格式化的文本块:
    #
    #   请求行: GET /path HTTP/1.1
    #   Host 头是 HTTP/1.1 必须的 (虚拟主机需要知道你要访问哪个域名)
    #   Connection: close → 告诉服务器 "发完就关", 不用 keep-alive
    #   User-Agent → 服务器日志和统计用
    #   Accept → 告诉服务器客户端能处理什么格式
    #
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"User-Agent: netcli/1.0 (Learning Tool)\r\n"
        f"Accept: */*\r\n"
        f"Connection: close\r\n"
        f"\r\n"  # ← 这个空行是 HTTP 协议的标记: "头部结束, 以下为请求体"
    )

    print(f"\n[2/3] 发送 HTTP 请求 ({len(request)} 字节):")
    # 把 \r\n 显示出来, 帮助理解格式
    for line in request.split('\r\n'):
        if line:
            print(f"  ▎ {line}")
        else:
            print(f"  ▎ (空行 — 头部结束标记)")

    # HTTPS 需要先做 TLS 握手
    if scheme == 'https':
        print("\n  🔒 升级到 TLS...")
        # TLS 1.2 握手简化过程:
        #   1. ClientHello  → 客户端支持的密码套件 + 随机数
        #   2. ServerHello  → 服务端选的密码套件 + 随机数 + 证书
        #   3. 客户端验证证书 (CA 签名链)
        #   4. 密钥交换 (ECDHE 或 RSA), 双方算出对称密钥
        #   5. Finished → 后续全用对称加密
        #
        # python 的 ssl.wrap_socket 帮我们做了上面全部事情
        ctx = ssl.create_default_context()
        sock = ctx.wrap_socket(sock, server_hostname=host)
        # server_hostname 参数很重要:
        #   → TLS SNI (Server Name Indication) 扩展, 告诉服务器你要访问哪个域名
        #   → 没有 SNI 的话, 一个 IP 只能服务一个 HTTPS 站点
        info("TLS 版本", sock.version())
        cipher = sock.cipher()
        info("密码套件", f"{cipher[0]} (密钥长度 {cipher[2]} bits)")

    sock.sendall(request.encode())

    # ── 步骤 3: 接收并解析 HTTP 响应 ──
    print(f"\n[3/3] 接收 HTTP 响应...")
    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk

    sock.close()
    info("接收大小", f"{len(response)} 字节")

    # 解析 HTTP 响应
    # 响应格式: 状态行\r\n头部1\r\n头部2\r\n...\r\n\r\n响应体
    if b'\r\n\r\n' in response:
        header_part, body = response.split(b'\r\n\r\n', 1)
        header_lines = header_part.decode('utf-8', errors='replace').split('\r\n')

        # 状态行: HTTP/1.1 200 OK
        print(f"\n  ── 状态行 ──")
        print(f"  {header_lines[0]}")

        # 响应头
        print(f"\n  ── 响应头 ──")
        for line in header_lines[1:]:
            if ':' in line:
                key, val = line.split(':', 1)
                print(f"  {key:25s}: {val.strip()}")
            else:
                print(f"  {line}")

        # 响应体 (截断)
        print(f"\n  ── 响应体 ({len(body)} 字节) ──")
        body_text = body.decode('utf-8', errors='replace')
        if len(body_text) > 1000:
            print(f"  {body_text[:500]}")
            print(f"  ... (省略 {len(body_text) - 1000} 字符) ...")
            print(f"  {body_text[-500:]}")
        else:
            print(body_text)
    else:
        print(f"  ⚠️ 响应不完整或不是 HTTP 格式")
        print(f"  {response[:500]}")


# ═══════════════════════════════════════════════════════════════════════
# 3. dns — DNS 解析
# ═══════════════════════════════════════════════════════════════════════
#
# DNS 查询流程 (以浏览器输入 www.example.com 为例):
#
#   1. 浏览器缓存? → 没有
#   2. OS 缓存 (nscd/systemd-resolved)? → 没有
#   3. /etc/hosts? → 没有
#   4. DNS 服务器 (递归查询):
#
#      客户端                     DNS 递归服务器              权威服务器
#      ──────                     ────────────              ────────
#      "www.example.com A?"  ──→  1. 问根服务器 (.) → 返回 .com NS
#                                 2. 问 .com 服务器 → 返回 example.com NS
#                                 3. 问 example.com 服务器 → 返回 A 记录
#      ←── 93.184.216.34 ────   缓存结果, 下次直接返回
#
#   DNS 记录类型:
#     A     — IPv4 地址
#     AAAA  — IPv6 地址
#     CNAME — 别名 (Canonical Name), 指向另一个域名
#     MX    — 邮件服务器
#     NS    — 域名服务器
#     TXT   — 文本记录 (SPF/DKIM 等)
#     SOA   — 权威记录起始 (Start of Authority)
#
# 我们用系统调用 getaddrinfo() 来触发 DNS 解析, 同时打印每个步骤。
# ======================================================================

def cmd_dns(args):
    """DNS 查询"""
    domain = args.domain

    hr(f"DNS 解析: {domain}")

    # ── 步骤 1: 检查 /etc/hosts ──
    print(f"\n[检查顺序]")
    print(f"  1. 浏览器/应用 DNS 缓存")
    print(f"  2. OS DNS 缓存 (mDNSResponder / systemd-resolved)")
    print(f"  3. /etc/hosts 文件")
    print(f"  4. 配置的 DNS 服务器 (递归查询)")

    # ── 步骤 2: 查 /etc/hosts ──
    print(f"\n[/etc/hosts 检查]")
    found_in_hosts = False
    try:
        with open('/etc/hosts', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if domain in parts[1:]:
                        print(f"  ✓ 在 /etc/hosts 找到: {parts[0]} → {domain}")
                        found_in_hosts = True
    except Exception:
        print(f"  (无法读取 /etc/hosts)")

    if not found_in_hosts:
        print(f"  /etc/hosts 中未找到, 继续 DNS 查询...")

    # ── 步骤 3: 系统调用 getaddrinfo() ──
    # 这个调用会让 OS 走完整的 DNS 解析链:
    #   → 查 OS 缓存 → 查 /etc/hosts → 向 DNS 服务器发 UDP 包 (端口 53)
    #
    # DNS 协议底层是 UDP (大部分查询), 包格式 (DNS wire format):
    #   Header (12字节):  Transaction ID | Flags | Questions | Answer RRs | ...
    #   Question:          QNAME (域名, 分段编码) | QTYPE (A=1, AAAA=28) | QCLASS (IN=1)
    #   Answer:            NAME | TYPE | CLASS | TTL | RDLENGTH | RDATA
    #
    # 域名编码: "www.example.com" → 3'w''w''w' 7'e''x''a''m''p''l''e' 3'c''o''m' 0
    #   每个 label 前面加一个长度字节, 最后以 0 结尾
    print(f"\n[DNS 查询: getaddrinfo({domain})]")

    # IPv4 (A 记录)
    try:
        results = socket.getaddrinfo(domain, None, socket.AF_INET, socket.SOCK_STREAM)
        print(f"\n  ── A 记录 (IPv4) ──")
        seen = set()
        for r in results:
            ip = r[4][0]
            if ip not in seen:
                info("IPv4", ip)
                seen.add(ip)
    except socket.gaierror as e:
        print(f"  IPv4 解析失败: {e}")

    # IPv6 (AAAA 记录)
    try:
        results = socket.getaddrinfo(domain, None, socket.AF_INET6, socket.SOCK_STREAM)
        print(f"\n  ── AAAA 记录 (IPv6) ──")
        seen = set()
        for r in results:
            ip = r[4][0]
            if ip not in seen:
                info("IPv6", ip)
                seen.add(ip)
    except socket.gaierror as e:
        print(f"  IPv6 解析失败: {e}")

    # ── 步骤 4: 查看系统 DNS 配置 ──
    print(f"\n[系统 DNS 配置: /etc/resolv.conf]")
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    print(f"  {line}")
    except Exception:
        print(f"  (无法读取)")

    # ── 额外: 手动构造一个 DNS 查询包展示 ──
    if args.verbose:
        print(f"\n[DNS 协议细节]")
        print(f"  传输层: UDP (端口 53), TCP 用于大响应(>512B)或区域传送")
        print(f"  查询包示例 (请求 {domain} 的 A 记录):")
        print(f"    Header:  ID=0x1234, QR=0(查询), OPCODE=0(标准)")
        print(f"              RD=1(期望递归), QDCOUNT=1")
        print(f"    Question: QNAME={domain}, QTYPE=1(A), QCLASS=1(IN)")


# ═══════════════════════════════════════════════════════════════════════
# 4. ifaces — 查看本机网络接口
# ═══════════════════════════════════════════════════════════════════════
#
# 每个网络接口 (网卡) 可以绑定多个 IP 地址。
# 常见的接口:
#   lo0 / lo       — 回环接口 (127.0.0.1, ::1), 只在本机内部通信
#   en0 / eth0     — 有线/无线网卡 (物理接口)
#   utun / tun     — VPN 隧道虚拟接口
#   bridge / docker— 虚拟网桥
#
# INADDR_ANY (0.0.0.0) 的含义:
#   bind 到 0.0.0.0 → 接收发往本机所有 IP 的包
#   bind 到 127.0.0.1 → 只接收本地回环请求
#   bind 到 192.168.1.5 → 只接收发往这个具体 IP 的包
# ======================================================================

def cmd_ifaces(args):
    """查看网络接口"""
    hr("本机网络接口")

    # Python 标准库没有直接列出接口的 API, 但我们可以用 ifaddr 的信息
    # 或者用 socket + ioctl / netifaces 思路
    # 这里用一个取巧的办法: 遍历常见接口名并查地址

    # getaddrinfo 查本机 hostname
    hostname = socket.gethostname()
    info("主机名", hostname)

    print(f"\n  ── 各接口地址 ──")
    # 方法: socket.getaddrinfo(socket.gethostname(), None)
    try:
        ip_list = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        seen = set()
        for r in ip_list:
            ip = r[4][0]
            family = "IPv4" if r[0] == socket.AF_INET else "IPv6"
            if ip not in seen:
                info(family, ip)
                seen.add(ip)

        # 也显式列出常见地址
        info("localhost (loopback)", "127.0.0.1 / ::1")
    except socket.gaierror as e:
        print(f"  获取失败: {e}")

    # 尝试用系统工具
    import subprocess
    print(f"\n  ── 系统工具输出 ──")
    try:
        result = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5)
        # 只提取 IP 相关的行
        for line in result.stdout.split('\n'):
            line = line.strip()
            if 'inet ' in line or 'inet6 ' in line:
                print(f"  {line}")
    except Exception:
        # macOS 没有 ip 命令, 用 ifconfig
        try:
            result = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'inet ' in line or 'inet6 ' in line:
                    print(f"  {line}")
        except Exception as e:
            print(f"  (无法获取: {e})")


# ═══════════════════════════════════════════════════════════════════════
# 5. listen — 启动简易 TCP 服务端
# ═══════════════════════════════════════════════════════════════════════
#
# 走完整 server 端流程, 与之前的 C 版本 echoServer 对应。
# 非常适合配合 connect 命令使用 (一个终端 netcli listen, 另一个 netcli connect)
# ======================================================================

def cmd_listen(args):
    """启动简易 TCP 服务端 (走通 socket-bind-listen-accept-recv-send)"""
    port = args.port

    hr(f"TCP Server 启动: 0.0.0.0:{port}")

    # [1] socket()
    print("\n[1/5] socket() — 创建 socket")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    info("listen_fd", server.fileno())
    info("内核", "struct socket (SS_UNCONNECTED) + struct inet_sock")

    # [2] bind()
    print("\n[2/5] bind() — 绑定地址端口")
    server.bind(('0.0.0.0', port))
    info("绑定地址", f"0.0.0.0:{port}")
    info("内核", "inet_sock.rcv_saddr=0.0.0.0, sport=port → 插入 bind_hash_table")

    # [3] listen()
    print("\n[3/5] listen() — 标记被动 socket")
    server.listen(5)
    info("内核", "TCP_LISTEN → SYN 队列 + ACCEPT 队列已分配")
    info("bl", f"5 (ACCEPT 队列最大长度 = min(5, somaxconn))")

    print(f"\n[4/5] 等待客户端连接... (本机: localhost:{port})")
    print(f"  另开终端运行: python3 netcli.py connect localhost {port}")

    # [4] accept() + [5] recv/send
    client_count = 0
    try:
        while True:
            print(f"\n  ── 等待下一个连接... ──")
            conn, addr = server.accept()
            client_count += 1
            print(f"  ✓ 客户端 #{client_count}: {addr[0]}:{addr[1]}")
            info("conn_fd", conn.fileno())
            print(f"  内核: 从 ACCEPT 队列取出 struct sock → 创建新 fd")

            # 收发循环
            total_recv = 0
            while True:
                data = conn.recv(4096)
                if not data:
                    print(f"  ← 收到 FIN (客户端关闭), 共收 {total_recv} 字节")
                    break
                total_recv += len(data)
                text = data.decode('utf-8', errors='replace').rstrip()
                print(f"  ← recv {len(data)}B: \"{text}\"")
                # Echo 回去
                conn.sendall(data)
                print(f"  → send {len(data)}B (echo)")

            conn.close()
            print(f"  close() → 发送 FIN (被动端: ESTABLISHED → CLOSE_WAIT → LAST_ACK → CLOSED)\n")

    except KeyboardInterrupt:
        print(f"\n\n  服务端关闭 (共处理 {client_count} 个客户端)")
    finally:
        server.close()


# ═══════════════════════════════════════════════════════════════════════
# 6. proxy — 简易 HTTP 正向代理
# ═══════════════════════════════════════════════════════════════════════
#
# HTTP 正向代理的工作原理:
#
#   浏览器                   代理服务端                 目标服务器
#   ──────                   ────────                 ────────
#   "我想访问 baidu.com" ──→
#   (配置了代理 = 代理IP:port)
#                           "GET http://baidu.com/ HTTP/1.1" ──→
#                           ←── 200 OK ──
#   ←── 200 OK ──
#
# 关键区别:
#   没有代理: GET / HTTP/1.1 + Host: baidu.com
#   有代理:   GET http://baidu.com/ HTTP/1.1 + Host: baidu.com
#             代理通过绝对 URI 知道你要访问哪个服务器
#
# 代理能看到你访问的所有内容 → MITM 中间人
# HTTPS 代理用 CONNECT 方法, 代理只转发 TLS 加密流, 看不到内容
# ======================================================================

def cmd_proxy(args):
    """启动简易 HTTP 代理"""
    port = args.port
    hr(f"HTTP 正向代理: 0.0.0.0:{port}")

    print(f"\n  原理:")
    print(f"    浏览器配置代理 = localhost:{port}")
    print(f"    浏览器把请求发给代理, 代理转发给真正服务器")
    print(f"    代理可以看到/修改所有 HTTP 明文内容 (中间人)")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', port))
    server.listen(5)
    print(f"\n  代理启动: localhost:{port}")
    print(f"  测试: curl -x http://localhost:{port} http://httpbin.org/get\n")

    try:
        while True:
            conn, addr = server.accept()
            print(f"\n  ✓ 新客户端: {addr[0]}:{addr[1]}")

            # 接收客户端请求
            request = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                request += chunk
                if b'\r\n\r\n' in request:
                    break

            if not request:
                conn.close()
                continue

            # 解析请求, 提取目标地址
            request_text = request.decode('utf-8', errors='replace')
            first_line = request_text.split('\r\n')[0]
            print(f"  请求行: {first_line}")

            # 解析绝对 URI: GET http://host:port/path HTTP/1.1
            m = re.match(r'(\S+)\s+http://([^/:]+)(?::(\d+))?(/\S*)?\s+HTTP', first_line)
            if not m:
                print(f"  ⚠️ 不是代理格式请求, 跳过")
                conn.close()
                continue

            method, target_host, target_port_str, target_path = m.groups()
            target_port = int(target_port_str) if target_port_str else 80
            target_path = target_path if target_path else '/'
            print(f"  → 目标: {target_host}:{target_port}{target_path}")

            # 转发到目标服务器
            try:
                upstream = socket.create_connection((target_host, target_port), timeout=10)
                # 重写请求行 (去掉 http://host 前缀)
                fwd = f"{method} {target_path} HTTP/1.1\r\n"
                for line in request_text.split('\r\n')[1:]:
                    if line.lower().startswith('proxy-'):
                        continue
                    fwd += line + '\r\n'
                fwd += '\r\n'
                upstream.sendall(fwd.encode())

                # 转发响应
                while True:
                    chunk = upstream.recv(4096)
                    if not chunk:
                        break
                    conn.sendall(chunk)
                upstream.close()
                print(f"  ✓ 请求完成")
            except Exception as e:
                print(f"  ❌ 代理错误: {e}")
                conn.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            finally:
                conn.close()

    except KeyboardInterrupt:
        print(f"\n\n  代理关闭")
    finally:
        server.close()


# ═══════════════════════════════════════════════════════════════════════
# main — CLI 入口
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='netcli — 计算机网络学习 CLI 工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 netcli.py connect example.com 80
  python3 netcli.py http http://httpbin.org/get
  python3 netcli.py dns www.baidu.com
  python3 netcli.py dns www.baidu.com --verbose
  python3 netcli.py ifaces
  python3 netcli.py listen 9999
  python3 netcli.py proxy 8888
        """
    )
    sub = parser.add_subparsers(dest='command', help='子命令')

    # connect
    p = sub.add_parser('connect', help='TCP connect + 收发数据')
    p.add_argument('host', help='目标地址')
    p.add_argument('port', type=int, help='目标端口')
    p.add_argument('-d', '--data', help='要发送的数据 (默认对80端口发HTTP GET)')
    p.add_argument('-i', '--interactive', action='store_true',
                   help='交互模式: 发完不关写端, 可继续打字 (Ctrl+D 退出)')
    p.add_argument('-t', '--timeout', type=float, default=None,
                   help='recv 超时秒数 (默认无限等待)')

    # http
    p = sub.add_parser('http', help='HTTP GET 请求')
    p.add_argument('url', help='URL (http://...)')

    # dns
    p = sub.add_parser('dns', help='DNS 解析')
    p.add_argument('domain', help='域名')
    p.add_argument('-v', '--verbose', action='store_true', help='显示 DNS 协议细节')

    # ifaces
    sub.add_parser('ifaces', help='查看本机网络接口')

    # listen
    p = sub.add_parser('listen', help='启动 TCP Echo Server')
    p.add_argument('port', type=int, help='监听端口')

    # proxy
    p = sub.add_parser('proxy', help='启动 HTTP 正向代理')
    p.add_argument('port', type=int, help='代理端口')

    args = parser.parse_args()

    if args.command == 'connect':
        cmd_connect(args)
    elif args.command == 'http':
        cmd_http(args)
    elif args.command == 'dns':
        cmd_dns(args)
    elif args.command == 'ifaces':
        cmd_ifaces(args)
    elif args.command == 'listen':
        cmd_listen(args)
    elif args.command == 'proxy':
        cmd_proxy(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
