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
/*
创建socket()
int socket(int domain, 
int type, 
int protocol);
domian = IPv4
type = sock_stream（TCP）
protocol = 0(自动选择，对他就是IPPROTO_TCP)
 * ── 内核里发生了什么 ──
 * 1. 内核分配一个 struct socket (通用 socket 层):
 *
 *    struct socket {
 *        socket_state  state;       // 初始 = SS_UNCONNECTED
 *        struct proto_ops *ops;     // 函数指针表: connect, bind, listen, accept, sendmsg, recvmsg ...
 *        struct file     *file;     // 关联到 VFS 的文件对象Virtual File System，虚拟文件系统
 *        struct sock     *sk;       // 指向协议族特定的 sock
 *    };
 * 调用 connect(fd, ...)
 *  → VFS 通过 fd 找到 struct file
 *  → file 找到 struct socket
 *  → socket->ops->connect() 
 * 调用具体协议的 connect 
 * → 具体协议（如 TCP）在 struct sock 
 * 里更新状态机、发起三次握手。
就像俄罗斯套娃：VFS（文件层）
→ struct socket（通用 socket 层）
→ proto_ops（协议操作层）
→ struct sock（协议状态层）。

 * 2. 内核分配 struct sock 
 (传输层，也叫 "sock" 或 "inet_sock" 对于 AF_INET):
 *
 *    struct inet_sock {
 *        struct sock   sk;          // 通用 sock
 *        __be32        inet_daddr;  // 目的 IP
 *        __be32        inet_rcv_saddr; // 绑定 IP (bind 或 connect 后设置)
 *        __be16        inet_dport;  // 目的端口
 *        __be16        inet_sport;  // 源端口 (bind 后 / connect 后自动分配)
 *    };
 *    
 * sock它由具体协议分配
 * （TCP 的 tcp_sock、UDP 的 udp_sock
 *  都内嵌了 struct sock），里面放的是
 * 协议真正关心的东西：
 * 发送/接收缓冲区、seq 号、
 * 拥塞控制状态、重传队列等等。

*/
int creat_socket()
{
    int listen_fd;

    printf("═══════════════════════════════════════════\n");
    printf("[1] socket() — 创建 socket\n");
    printf("═══════════════════════════════════════════\n");

    listen_fd = socket(AF_INET,SOCK_STREAM,0);
    if (listen_fd < 0){
        perror("socket");
        exit(EXIT_FAILURE);
    }

    printf("-> return fd = %d\n", listen_fd);
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
     * socket() → setsockopt(SO_REUSEADDR) 
     * → bind() → listen() → accept()
     */

    {
        int yes = 1;
        if (setsockopt(listen_fd,SOL_SOCKET,SO_REUSEADDR,&yes,
        sizeof(yes)
        )<0){
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }
    }
    printf("→ 设置 SO_REUSEADDR: 允许重用 TIME_WAIT 状态的端口\n\n");

    return listen_fd;
}


void bind_socket(int listen_fd)
{
    struct sockaddr_in addr;

    printf("═══════════════════════════════════════════\n");
    printf("[2] bind() — 绑定地址和端口\n");
    printf("═══════════════════════════════════════════\n");

    memset(&addr,0,sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(PORT);

    printf("→ 准备绑定地址:\n");
    printf("    sin_family      = AF_INET (IPv4)\n");
    printf("    sin_addr.s_addr = INADDR_ANY (0.0.0.0)\n");
    printf("    sin_port        = htons(%d) = 0x%04x\n\n", PORT, ntohs(addr.sin_port));
    
    if (bind(listen_fd,(struct sockaddr *)&addr,sizeof(addr))<0){
        perror("bind");
        exit(EXIT_FAILURE);
    }
}



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

int accept_connection(int listen_fd,char* client_ip,size_t ip_len,
                    int* client_port)
{
    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);
    int conn_fd;

    printf("═══════════════════════════════════════════\n");
    printf("[4] accept() — 从 ACCEPT 队列取出连接\n");
    printf("═══════════════════════════════════════════\n");

    printf("→ 阻塞等待 ACCEPT 队列... (进程进入 TASK_INTERRUPTIBLE 睡眠)\n");

    conn_fd = accept(listen_fd,(struct sockaddr*)&client_addr,&addr_len);
    if (conn_fd <0){
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

