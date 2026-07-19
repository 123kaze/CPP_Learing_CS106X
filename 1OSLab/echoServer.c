/*
 * echoServer.c — 从零手写 TCP Echo Server，走通五个系统调用
 *
 * 编译: gcc -Wall -o echoServer echoServer.c
 * 运行: ./echoServer
 * 测试: 另开终端，nc localhost 8080，输入任意文字回车，服务器原样返回
 *
 * 五个系统调用:
 *   socket() → bind() → listen() → accept() → read()/write()
 *
 * 每个调用背后对应内核中的数据结构和状态变化，代码中逐段注释。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

/* ===== Socket 相关头文件 ===== */
#include <sys/socket.h>   /* socket(), bind(), listen(), accept() */
#include <netinet/in.h>   /* struct sockaddr_in, htons(), INADDR_ANY */
#include <arpa/inet.h>    /* inet_ntop(), inet_pton() */

#define PORT    8080
#define BACKLOG 5        /* listen 队列长度（经典值 5，实际内核会乘以 1.5） */
#define BUF_SIZE 4096


/* ======================================================================
 * 第一步: socket() — 创建 socket
 *
 * 函数原型:
 *   int socket(int domain, int type, int protocol);
 *
 * 参数:
 *   domain   = AF_INET  (IPv4)
 *   type     = SOCK_STREAM (TCP, 面向流)
 *   protocol = 0 (自动选择，对 SOCK_STREAM 就是 IPPROTO_TCP)
 *
 * 返回值: 一个文件描述符（fd），内核通过 fd 关联到 socket 对象。
 *
 * ── 内核里发生了什么 ──
 *
 * 1. 内核分配一个 struct socket (通用 socket 层):
 *
 *    struct socket {
 *        socket_state  state;       // 初始 = SS_UNCONNECTED
 *        struct proto_ops *ops;     // 函数指针表: connect, bind, listen, accept, sendmsg, recvmsg ...
 *        struct file     *file;     // 关联到 VFS 的文件对象Virtual File System，虚拟文件系统
 *        struct sock     *sk;       // 指向协议族特定的 sock
 *    };
 *
 * 2. 内核分配 struct sock (传输层，也叫 "sock" 或 "inet_sock" 对于 AF_INET):
 *
 *    struct inet_sock {
 *        struct sock   sk;          // 通用 sock
 *        __be32        inet_daddr;  // 目的 IP
 *        __be32        inet_rcv_saddr; // 绑定 IP (bind 或 connect 后设置)
 *        __be16        inet_dport;  // 目的端口
 *        __be16        inet_sport;  // 源端口 (bind 后 / connect 后自动分配)
 *    };
 *
 * 3. 进程的 fd table[fd] → struct file → struct socket → struct sock
 *
 *    用户态        VFS 层              BSD Socket 层       传输层
 *    fd=3    →   struct file    →   struct socket    →   struct sock
 *    (int)       (f_op=...)         (ops=..., sk=...)     (状态, 缓冲区...)
 *
 * 4. 状态: 此时 socket 处于 CLOSED / SS_UNCONNECTED，还没绑定地址。
 *    这只是在内存里建好了数据结构，网卡驱动还不知道这个 socket 的存在。
 * ====================================================================== */
int create_socket()
{
    int listen_fd;

    printf("═══════════════════════════════════════════\n");
    printf("[1] socket() — 创建 socket\n");
    printf("═══════════════════════════════════════════\n");

    listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    printf("→ 返回 fd = %d\n", listen_fd);
    printf("→ 内核分配: struct socket (状态=SS_UNCONNECTED)\n"
           "              └── struct inet_sock (源端口=0, 目的端口=0)\n"
           "→ 没有任何地址绑定, 网卡驱动不知道它存在\n\n");

    /*
     * SO_REUSEADDR — 允许重用处于 TIME_WAIT 的本地地址
     *
     * 什么时候出问题?
     *   你 Ctrl+C 杀掉服务器, 主动 close 的那端进入 TIME_WAIT (2MSL ≈ 60s)。
     *   在此期间内核不让你 bind 同一个端口, 会报 EADDRINUSE。
     *
     * SO_REUSEADDR 做了什么?
     *   告诉内核: "如果端口处于 TIME_WAIT, 允许我 bind"。但不允许
     *   两个活跃的 socket 同时 bind 同一个端口 (那才算真正的冲突)。
     *
     * 正确的做法:
     *   在 bind() 之前设置, 让开发/调试不浪费时间等 60 秒。
     */
    {
        int yes = 1;
        if (setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)) < 0) {
            perror("setsockopt");
            exit(EXIT_FAILURE);
        }
    }
    printf("→ 设置 SO_REUSEADDR: 允许重用 TIME_WAIT 状态的端口\n\n");

    return listen_fd;
}


/* ======================================================================
 * 第二步: bind() — 绑定地址和端口
 *
 * 函数原型:
 *   int bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
 *
 * 参数:
 *   sockfd   = socket() 返回的 fd
 *   addr     = 指向 sockaddr_in 的指针 (强制转型为 sockaddr*)
 *              - sin_family      = AF_INET
 *              - sin_addr.s_addr = INADDR_ANY (绑定所有网卡 IP)
 *              - sin_port        = htons(8080)
 *   addrlen  = sizeof(sockaddr_in)
 *
 * ── 内核里发生了什么 ──
 *
 * 1. 内核从 fd 找到 struct socket → struct sock (inet_sock)。
 *
 * 2. 遍历内核的绑定哈希表 (bind_hash_table)，检查 (IP, port) 是否已被占用:
 *    - 如果端口已经被其他 socket 绑定 → 返回 -EADDRINUSE
 *    - 如果设置了 SO_REUSEADDR + 旧 socket 处于 TIME_WAIT → 允许
 *
 * 3. 将地址写入 inet_sock:
 *    inet_sock.inet_rcv_saddr = INADDR_ANY  // 接收所有网卡的包
 *    inet_sock.inet_sport     = 8080        // 网络字节序
 *
 * 4. 将 sock 插入 bind_hash_table, 这样后续到达的数据包能找到这个 socket。
 *
 * 5. 此时 socket 状态仍然是 SS_UNCONNECTED (还没 listen, 不能接收连接)。
 * ====================================================================== */
void bind_socket(int listen_fd)
{
    struct sockaddr_in addr;

    printf("═══════════════════════════════════════════\n");
    printf("[2] bind() — 绑定地址和端口\n");
    printf("═══════════════════════════════════════════\n");

    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;          // IPv4
    addr.sin_addr.s_addr = htonl(INADDR_ANY); // 0.0.0.0, 监听所有网卡
    addr.sin_port        = htons(PORT);       // 8080, 网络字节序 (大端)

    /*
     * htons() 是什么?
     *   Host TO Network Short — 将本机字节序转为网络字节序 (大端/Big-Endian)。
     *   网络协议规定多字节整数用大端传输，而 x86 和 ARM 都是小端。
     *   8080 = 0x1F90, 小端是 0x90 0x1F, 大端是 0x1F 0x90。
     *   如果忘了 htons(), 在小端机器上会绑定到端口 36879 (0x901F)。
     */

    printf("→ 准备绑定地址:\n");
    printf("    sin_family      = AF_INET (IPv4)\n");
    printf("    sin_addr.s_addr = INADDR_ANY (0.0.0.0)\n");
    printf("    sin_port        = htons(%d) = 0x%04x\n\n", PORT, ntohs(addr.sin_port));

    if (bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        exit(EXIT_FAILURE);
    }

    printf("→ 内核做了三件事:\n");
    printf("  1. 检查 (0.0.0.0:8080) 是否冲突 → 无冲突\n");
    printf("  2. 写入 inet_sock: rcv_saddr=0.0.0.0, sport=8080\n");
    printf("  3. 插入 bind_hash_table，数据包到达时能路由到此 socket\n\n");
}


/* ======================================================================
 * 第三步: listen() — 标记为被动 socket, 准备接收连接
 *
 * 函数原型:
 *   int listen(int sockfd, int backlog);
 *
 * 参数:
 *   sockfd  = 已 bind 的 fd
 *   backlog = 连接队列的最大长度
 *
 * ── 内核里发生了什么 ──
 *
 * 1. 将 socket 状态从 SS_UNCONNECTED 转换为 TCP_LISTEN。
 *    此后它可以接收 SYN 包了。
 *
 * 2. 内核为这个 listening socket 分配两个队列:
 *
 *    客户端              ┌── SYN 队列 ──┐        ┌── ACCEPT 队列 ──┐
 *                      (半连接队列)           (已完成连接队列)
 *    send SYN ─────→  [SYN_RCVD]              [ESTABLISHED]
 *                         │                        │
 *    recv SYN+ACK ←───(连接在此)                 (连接在此)
 *    send ACK  ─────→   │  ──三次握手完成──→   移动到 ACCEPT 队列
 *                         │                        │
 *                                              accept() 从这里取
 *
 *    SYN 队列: 存放收到 SYN 但尚未完成三次握手的连接 (状态: SYN_RCVD)
 *    ACCEPT 队列: 存放已完成三次握手的连接 (状态: ESTABLISHED)，等待 accept() 取走
 *
 * 3. backlog 参数的含义 (Linux):
 *    - 历史上: 两个队列长度之和的上限
 *    - Linux 实际: ACCEPT 队列的最大长度
 *      /proc/sys/net/core/somaxconn 是系统级上限 (默认 4096)
 *      listen(fd, 5) 且 somaxconn=4096 → ACCEPT 队列实际长度 = min(5, 4096) = 5
 *
 * 4. 队列满了怎么办?
 *    - 新 SYN 到达时 ACCEPT 队列已满 → 内核默认丢弃 SYN (不回复 RST)
 *    - 这样客户端会超时重传 SYN, 给服务器争取时间
 *    - 可以在 /proc/sys/net/ipv4/tcp_abort_on_overflow 改为发送 RST
 *
 * 经典场景: "nginx 的 backlog 设多大?"
 *   通常设 511 (内核的上限在较老内核), 现代内核设 4096。
 *   本质上是 "瞬时能排队多少个新连接"。如果 accept() 处理够快,
 *   队列几乎总是空的，backlog 不需要太大。
 * ====================================================================== */
void start_listen(int listen_fd)
{
    printf("═══════════════════════════════════════════\n");
    printf("[3] listen() — 标记被动 socket, 设置 backlog\n");
    printf("═══════════════════════════════════════════\n");

    if (listen(listen_fd, BACKLOG) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    printf("→ 状态转换: SS_UNCONNECTED → TCP_LISTEN\n");
    printf("→ 内核分配两个队列:\n");
    printf("    SYN 队列 (未完成连接): 存放 SYN_RCVD 状态的半连接\n");
    printf("    ACCEPT 队列 (已完成连接): 存放 ESTABLISHED 状态的连接\n");
    printf("→ backlog = %d (实际 = min(%d, somaxconn))\n", BACKLOG, BACKLOG);
    printf("→ 此后内核会替我们完成 TCP 三次握手!\n");
    printf("→ 服务器监听 0.0.0.0:%d ...\n\n", PORT);
}


/* ======================================================================
 * 第四步: accept() — 从 ACCEPT 队列取出一个已完成握手的连接
 *
 * 函数原型:
 *   int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen);
 *
 * 参数:
 *   sockfd  = listening fd
 *   addr    = (出参) 内核把客户端的 IP+端口填到这里
 *   addrlen = (入参&出参) addr 的大小
 *
 * 返回值: 一个新的 fd (connected socket fd), 用于和这个客户端通信。
 *         原始的 listen_fd 仍然存在, 继续接收新连接。
 *
 * ── 内核里发生了什么 ──
 *
 * 1. 检查 ACCEPT 队列是否为空:
 *    - 空 + 阻塞模式 (默认): 进程进入睡眠 (TASK_INTERRUPTIBLE),
 *      等待有连接完成三次握手时被唤醒。
 *    - 空 + 非阻塞模式 (O_NONBLOCK): 返回 -EAGAIN。
 *
 * 2. 队列非空: 从 ACCEPT 队列头部取出一个 struct sock。
 *
 * 3. 内核基于这个 struct sock 创建一个新的 struct socket + struct file,
 *    分配一个新的 fd。这就是 "connected socket"。
 *
 * 4. 将客户端的 IP 和端口写入 addr (出参)。
 *
 * 5. 返回新的 fd。
 *
 * 关键理解:
 *   listen_fd  ≠  返回的 fd
 *   listen_fd 只用来 accept, 永远不读写数据
 *   返回的 fd  用来和这一个客户端通信 (read/write)
 *   listen_fd 只有一个, 每个客户端对应一个不同的 connected fd
 *
 * 类比: 公司前台电话 (listen_fd) vs 分机号 (connected fd)
 *   前台总是同一个号码, 但每次转接给你的是不同的内部分机。
 * ====================================================================== */
int accept_connection(int listen_fd, char *client_ip, size_t ip_len, int *client_port)
{
    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);
    int conn_fd;

    printf("═══════════════════════════════════════════\n");
    printf("[4] accept() — 从 ACCEPT 队列取出连接\n");
    printf("═══════════════════════════════════════════\n");

    /* 阻塞等待, 直到 ACCEPT 队列非空 */
    printf("→ 阻塞等待 ACCEPT 队列... (进程进入 TASK_INTERRUPTIBLE 睡眠)\n");

    conn_fd = accept(listen_fd, (struct sockaddr *)&client_addr, &addr_len);
    if (conn_fd < 0) {
        perror("accept");
        return -1;
    }

    /* 提取客户端地址 */
    if (inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, ip_len) == NULL) {
        perror("inet_ntop");
        strcpy(client_ip, "unknown");
    }
    *client_port = ntohs(client_addr.sin_port);

    printf("→ 内核从 ACCEPT 队列头部取出一个 struct sock\n");
    printf("→ 创建新的 struct socket + struct file + 新 fd\n");
    printf("→ 新 fd = %d (connected socket), 客户端 %s:%d\n\n",
           conn_fd, client_ip, *client_port);

    return conn_fd;
}


/* ======================================================================
 * 第五步: read()/write() — 收发数据
 *
 * 函数原型:
 *   ssize_t read(int fd, void *buf, size_t count);
 *   ssize_t write(int fd, const void *buf, size_t count);
 *
 * ── 内核里发生了什么 (以 read 为例) ──
 *
 * 1. 内核从 fd 找到 struct file → struct socket → struct sock。
 *
 * 2. 检查 struct sock 的接收缓冲区 (sk_receive_queue):
 *    - 这是一个 sk_buff 链表, 每个 sk_buff 是一个收到的数据包。
 *
 *    ┌── sk_receive_queue ──────────────────────────────┐
 *    │ sk_buff[1] → sk_buff[2] → sk_buff[3]            │
 *    │   1KB          1KB          512B                 │
 *    │  "Hello"      "World"       "!\n"                │
 *    │   序列号 0      序列号 1024   序列号 2048         │
 *    └──────────────────────────────────────────────────┘
 *
 *    TCP 把乱序到达的包重排后才插入这个队列, 所以 read() 看到的是
 *    按序到达的字节流。TCP 保证顺序!
 *
 * 3. 缓冲区空 + 阻塞模式 → 进程睡眠, 等数据到达。
 *    缓冲区空 + 非阻塞 → 返回 -EAGAIN。
 *
 * 4. 数据就绪 → 内核从 sk_buff 链表里拷贝数据到用户态 buf。
 *    这是一个 copy_to_user() 操作, 数据从内核空间拷贝到用户空间。
 *
 * 5. read() 返回成功读取的字节数。
 *
 * ── read() 不保证一次读完 ──
 *
 *   这是 TCP 编程最经典的一个坑:
 *   发送端: write(fd, "HelloWorld", 10);
 *   接收端: read(fd, buf, 4096) 可能返回 5 ("Hello"), 需要再读一次拿 "World"。
 *
 *   原因: TCP 是字节流, 不是消息。内核可以任意分割合并数据。
 *   对端发了 10 个字节, 你可能分两次收到; 也可能一次读到两次 write 的数据。
 *
 *   解决方案: 应用层协议定义消息边界 (长度前缀、分隔符、定长消息等)。
 *   echo server 最简单: 读到 0 表示对端关闭, 读到啥就回啥。
 *
 * ── write() 同理 ──
 *
 *   内核先把数据拷贝到 struct sock 的发送缓冲区 (sk_write_queue, 也是 sk_buff 链表),
 *   然后 TCP 协议栈负责分片、加 TCP 头、传 IP 层、走网卡发出。
 *
 *   write() 也可能只写了部分数据 (缓冲区满), 需要循环写。
 * ====================================================================== */
void echo_loop(int conn_fd, const char *client_ip, int client_port)
{
    char buf[BUF_SIZE];
    ssize_t n;

    printf("═══════════════════════════════════════════\n");
    printf("[5] read()/write() — 收发数据 (Echo Loop)\n");
    printf("═══════════════════════════════════════════\n");
    printf("→ 客户端 %s:%d 已连接, fd=%d\n\n", client_ip, client_port, conn_fd);

    while (1) {
        printf("→ read() 阻塞等待数据...\n"
               "   内核检查 sk_receive_queue (sk_buff 链表)\n");

        n = read(conn_fd, buf, sizeof(buf));

        if (n < 0) {
            perror("read");
            break;
        } else if (n == 0) {
            /*
             * read() 返回 0 → 对端发送了 FIN
             *
             * 这意味着对端调用了 close() 或 shutdown(SHUT_WR)。
             * TCP 收到了 FIN 包, 四次挥手已走完一半:
             *   对端 → FIN → 我们 (我们进入 CLOSE_WAIT)
             *   我们 → ACK → 对端 (对端进入 FIN_WAIT_2)
             */
            printf("\n→ read() 返回 0 — 对端发送了 FIN\n");
            printf("→ 客户端 %s:%d 关闭了连接 (TCP 半关闭)\n\n", client_ip, client_port);
            break;
        }

        printf("→ 收到 %zd 字节: \"%.*s\"\n", n, (int)n, buf);
        printf("   (内核通过 copy_to_user 把 sk_buff 链表的数据拷到用户态 buf)\n");

        /*
         * Echo: 原样写回
         *
         * 注意: write() 也可能只写一部分 (send buffer 满时)。
         * 这里简单处理: 如果返回 < n, 实际应该循环 write 剩余部分。
         */
        {
            ssize_t written = write(conn_fd, buf, n);
            if (written < 0) {
                perror("write");
                break;
            }
            printf("→ 回写 %zd 字节 (内核拷贝到 sk_write_queue → TCP 分片 → IP → 网卡)\n\n",
                   written);
        }
    }
}


/* ======================================================================
 * close() — 关闭连接, 触发 TCP 四次挥手
 *
 *   主动 close 的一方:
 *   1. 发送 FIN (进入 FIN_WAIT_1)
 *   2. 收到 ACK (进入 FIN_WAIT_2)
 *   3. 收到对端的 FIN (进入 TIME_WAIT)
 *   4. 等待 2MSL (60s) 后真正关闭
 *
 *   被动 close 的一方:
 *   1. 收到 FIN (进入 CLOSE_WAIT)
 *   2. 发送 ACK
 *   3. 应用调用 close()
 *   4. 发送 FIN (进入 LAST_ACK)
 *   5. 收到 ACK → 释放
 *
 *   "为什么服务端 close() 后客户端还能发数据?"
 *   因为 close(conn_fd) 实际上只是发送了一个 FIN, 告诉对端"我不发了",
 *   但你仍然可以收数据, 直到对端也发 FIN。
 *   这就是 TCP 半关闭状态 (Half-Close):
 *   shutdown(fd, SHUT_WR) → 只关写端, 还能读
 *   close(fd)             → 读写都关 (但立即返回, 实际握手异步进行)
 * ====================================================================== */
void close_connection(int conn_fd, const char *client_ip, int client_port)
{
    printf("═══════════════════════════════════════════\n");
    printf("close() — 关闭连接\n");
    printf("═══════════════════════════════════════════\n");
    printf("→ 发送 FIN 到 %s:%d\n", client_ip, client_port);
    printf("→ TCP 状态转换:\n");
    printf("   主动端: ESTABLISHED → FIN_WAIT_1 → FIN_WAIT_2 → TIME_WAIT → CLOSED\n");
    printf("   被动端: ESTABLISHED → CLOSE_WAIT → LAST_ACK → CLOSED\n");
    printf("→ TIME_WAIT 持续 2MSL (约 60 秒), 确保最后的 ACK 能被对端收到\n");
    printf("   (这就是为什么你 Ctrl+C 后马上重启会报 EADDRINUSE)\n\n");

    close(conn_fd);
}


/* ======================================================================
 * main — 组装整个流程
 *
 * socket() → bind() → listen() → accept() → read()/write() → close()
 * ====================================================================== */
int main()
{
    int listen_fd, conn_fd;
    char client_ip[INET_ADDRSTRLEN];
    int  client_port;

    /* 1. socket() */
    listen_fd = create_socket();

    /* 2. bind() */
    bind_socket(listen_fd);

    /* 3. listen() */
    start_listen(listen_fd);

    /* 4. accept() + 5. read()/write() + close() */
    while (1) {
        conn_fd = accept_connection(listen_fd, client_ip, sizeof(client_ip), &client_port);
        if (conn_fd < 0)
            continue;

        echo_loop(conn_fd, client_ip, client_port);

        close_connection(conn_fd, client_ip, client_port);
    }

    /* 关闭 listen socket (实际上到不了这里, 但完整的程序应该处理信号) */
    close(listen_fd);
    return 0;
}
