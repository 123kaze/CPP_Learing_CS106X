#!/usr/bin/env python3
"""
bench.py — epoll echo server 并发压力测试

用法:
    python3 bench.py                     # 默认 100 连接, 10 消息/连接
    python3 bench.py 500 20              # 500连接, 20消息/连接
    python3 bench.py 2000 5 --port 8080  # 指定端口

测试模型:
    1. 并发建立 N 个连接 (线程池)
    2. 所有连接同时发消息
    3. 验证回显正确性
    4. 统计 QPS、延迟、吞吐
"""

import socket
import time
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor


def bench_one(args):
    """单个连接的工作: 建立连接 → 发 N_MSGS 条消息 → 验证回显 → 关闭"""
    conn_id, n_msgs, port = args
    send_total = 0

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("127.0.0.1", port))

        for j in range(n_msgs):
            msg = f"c={conn_id} m={j}".encode()
            sock.sendall(msg)

            # 接收回显 (确保读够 send 的长度)
            buf = b""
            while len(buf) < len(msg):
                chunk = sock.recv(len(msg) - len(buf))
                if not chunk:
                    return (conn_id, False, send_total, "recv returned empty (server closed)")
                buf += chunk

            if buf != msg:
                return (conn_id, False, send_total, f"data mismatch: sent={msg!r} recv={buf!r}")

            send_total += 1

        sock.close()
        return (conn_id, True, send_total, None)

    except Exception as e:
        return (conn_id, False, send_total, str(e))


def main():
    parser = argparse.ArgumentParser(description="epoll echo server 并发压测")
    parser.add_argument("conns", nargs="?", type=int, default=100,
                        help="并发连接数 (默认 100)")
    parser.add_argument("msgs", nargs="?", type=int, default=10,
                        help="每连接消息数 (默认 10)")
    parser.add_argument("--port", "-p", type=int, default=8080,
                        help="端口 (默认 8080)")
    parser.add_argument("--workers", "-w", type=int, default=50,
                        help="线程池大小 (默认 50)")
    args = parser.parse_args()

    N_CONN  = args.conns
    N_MSGS  = args.msgs
    PORT    = args.port
    WORKERS = min(args.workers, N_CONN)

    print("═══════════════════════════════════════════")
    print("  epoll Echo Server 并发压力测试")
    print("═══════════════════════════════════════════")
    print(f"  连接数:         {N_CONN}")
    print(f"  每连接消息数:    {N_MSGS}")
    print(f"  总消息数:        {N_CONN * N_MSGS}")
    print(f"  端口:            {PORT}")
    print(f"  线程池:          {WORKERS} workers")
    print("═══════════════════════════════════════════\n")

    # ── 阶段1: 并发建立连接 + 收发 ──
    print(f"[1/2] 并发建立 {N_CONN} 个连接并收发 {N_MSGS} 条消息/连接...")
    tasks = [(i, N_MSGS, PORT) for i in range(N_CONN)]

    t0 = time.time()
    ok = fail = total_msgs = 0
    errors = []

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for conn_id, success, msgs, err in pool.map(bench_one, tasks):
            total_msgs += msgs
            if success:
                ok += 1
            else:
                fail += 1
                errors.append((conn_id, err))

    t1 = time.time()
    elapsed = t1 - t0

    # ── 汇总 ──
    print(f"\n  ✓ 成功: {ok} 连接, ✗ 失败: {fail} 连接")
    print(f"  完成消息: {total_msgs} 次请求/响应")
    print(f"  总耗时:   {elapsed:.2f} 秒")
    print(f"  QPS:      {total_msgs / elapsed:.0f} 消息/秒")
    print(f"  吞吐:     {total_msgs * 20 / elapsed / 1024:.1f} KB/s (估算)")
    if errors:
        print(f"\n  错误 (前10):")
        for cid, err in errors[:10]:
            print(f"    conn={cid}: {err}")

    print("\n═══════════════════════════════════════════")

    if fail == 0:
        print("  ✓ 全部通过, 数据完整性正确")
    else:
        print(f"  ✗ {fail} 个连接失败")

    print("═══════════════════════════════════════════")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
