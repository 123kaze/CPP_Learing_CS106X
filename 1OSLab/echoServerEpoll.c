/*
 * echoServerEpoll.c — 单线程 epoll Reactor 模型 Echo Server
 *
 * 编译: gcc -Wall -o echoServerEpoll echoServerEpoll.c
 * 运行: ./echoServerEpoll
 * 测试: nc localhost 8080 (可以同时开多个终端连进来)
 *
 * =====================================================================
 * 与阻塞版 echoServer.c 的核心区别:
 *
 *   阻塞版 (单线程):
 *     while(1) { accept() → read()/write() → close() }
 *     一次只能处理一个客户端。read() 阻塞时, 别的客户端连 accept 都进不去。
 *
 *   epoll 版 (单线程):
 *     epoll_wait() 同时监视 listen_fd + 所有 conn_fd
 *     哪个 fd 有数据就处理哪个, 一个线程服务 N 个客户端。
 *     零锁、零竞争、零惊群、零上下文切换(除了系统调用本身)。
 *
 * =====================================================================
 * 内核数据结构回顾 (对照笔记):
 *
 *   socket.sk_wq:       每个 socket 的等待队列, epoll_ctl 把回调挂在这
 *   eventpoll.rbr:      红黑树, 存"我在看哪些 fd" (全集)
 *   eventpoll.rdllist:  就绪链表, 存"哪些 fd 现在有数据" (子集)
 *   eventpoll.wq:       epoll 自己的等待队列, epoll_wait 的线程挂在这里
 *
 *   数据到达链:
 *   网卡中断 → sk_receive_queue → sock_def_readable()
 *   → wake_up(sk_wq) → ep_poll_callback(epitem)
 *   → 挂 epitem 到 rdllist → wake_up(eventpoll.wq) → epoll_wait 返回
 *
 * =====================================================================
 * ET 模式注意事项:
 *   - 必须循环 read() 直到返回 EAGAIN, 否则剩余数据永远不会再触发事件
 *   - fd 必须设为非阻塞 (O_NONBLOCK), 否则最后一次 read 可能阻塞整个循环
 *   - accept() 也要循环直到 EAGAIN (高并发下 ACCEPT 队列可能积压多个连接)
 * =====================================================================
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>

#include <sys/socket.h>
#include <sys/epoll.h>      /* epoll_create1, epoll_ctl, epoll_wait, struct epoll_event */
#include <netinet/in.h>
#include <arpa/inet.h>

#define PORT        8080
#define BACKLOG     128
#define MAX_EVENTS  1024    /* epoll_wait 一次最多返回的事件数 */
#define BUF_SIZE    4096

/* ======================================================================
 * 工具函数: 将 fd 设为非阻塞模式
 *
 * 为什么必须非阻塞?
 *   在 ET 模式下, 必须循环 read() 直到返回 EAGAIN。
 *   如果 fd 是阻塞的, 最后一次 read() 会永远卡住, 整个事件循环就死了。
 *   设为非阻塞后, 缓冲区空 → 直接返回 -1 + EAGAIN, 不会阻塞。
 * ====================================================================== */
static void set_nonblocking(int fd)
{
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) {
        perror("fcntl F_GETFL");
        exit(EXIT_FAILURE);
    }
    if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
        perror("fcntl F_SETFL O_NONBLOCK");
        exit(EXIT_FAILURE);
    }
}


/* ======================================================================
 * socket() + bind() + listen() — 与阻塞版完全一致
 * 多了一步: 把 listen_fd 也设成非阻塞 (配合 ET 下循环 accept)
 * ====================================================================== */
static int create_listen_socket()
{
    int listen_fd, yes = 1;
    struct sockaddr_in addr;

    /* ---- socket() ---- */
    printf("[1] socket()\n");
    listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd < 0) { perror("socket"); exit(EXIT_FAILURE); }
    printf("    listen_fd = %d\n", listen_fd);

    setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));

    /* 设非阻塞: 配合 epoll ET 下的循环 accept (后面会看到) */
    set_nonblocking(listen_fd);
    printf("    已设为 O_NONBLOCK\n");

    /* ---- bind() ---- */
    printf("[2] bind(0.0.0.0:%d)\n", PORT);
    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port        = htons(PORT);
    if (bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind"); exit(EXIT_FAILURE);
    }

    /* ---- listen() ---- */
    printf("[3] listen(backlog=%d)\n", BACKLOG);
    if (listen(listen_fd, BACKLOG) < 0) {
        perror("listen"); exit(EXIT_FAILURE);
    }
    printf("    状态: SS_UNCONNECTED → TCP_LISTEN\n");
    printf("    监听 0.0.0.0:%d ...\n\n", PORT);

    return listen_fd;
}


/* ======================================================================
 * 处理客户端连接上的可读事件 (ET 模式)
 *
 * ET 模式下必须循环读, 直到返回 EAGAIN:
 *
 *   while ((n = read(fd, buf, sizeof(buf))) > 0) {
 *       ...处理...
 *   }
 *   if (n == 0)     → 对端关闭 (收到了 FIN)
 *   if (n == -1) {
 *       if (errno == EAGAIN) → 读完了, 正常退出循环
 *       else                 → 真正的错误, 关闭连接
 *   }
 *
 * ── 如果我只读一次就停会怎样? ──
 *   假设对端发了 8KB, 内核 sk_receive_queue 有 2 个 sk_buff (各 4KB)。
 *   你只 read 了 4KB → 回到 epoll_wait → ET 模式不会再报这个 fd!
 *   → 剩下 4KB 永远烂在缓冲区里, 客户端永远等不到回显。
 * ====================================================================== */
static void handle_client_read(int conn_fd)
{
    char buf[BUF_SIZE];
    ssize_t n;

    while (1) {
        n = read(conn_fd, buf, sizeof(buf));

        if (n > 0) {
            /*
             * 读到数据 → 原样写回
             *
             * 注意: write 也可能返回 -1 + EAGAIN (发送缓冲区满)。
             * 这里简化处理, 直接 write。生产环境应该:
             *   1. 维护应用层输出缓冲区
             *   2. 注册 EPOLLOUT, 等 fd 可写时再发
             */
            printf("  [fd=%d] 收到 %zd 字节: %.*s", conn_fd, n, (int)n, buf);
            if (buf[n-1] != '\n') printf("\n");

            ssize_t written = 0;
            while (written < n) {
                ssize_t w = write(conn_fd, buf + written, n - written);
                if (w < 0) {
                    if (errno == EAGAIN) {
                        /*
                         * 发送缓冲区满了。
                         *
                         * 简化处理: 跳过剩余数据 (生产环境应暂存到应用层
                         * 输出缓冲区, 等 EPOLLOUT 再发)。
                         *
                         * 客户端会看到不完整的回显——这是故意让学习者
                         * 看到"没处理 EPOLLOUT 会怎样"。
                         */
                        printf("  [fd=%d] 发送缓冲区满, 丢弃剩余 %zd 字节\n",
                               conn_fd, n - written);
                        goto done;
                    }
                    perror("write");
                    goto close_conn;
                }
                written += w;
            }
            printf("  [fd=%d] 回写 %zd 字节\n", conn_fd, written);
            continue;  /* 继续循环读下一批数据 */
        }

        if (n == 0) {
            /* read 返回 0 → 对端发送了 FIN → 四次挥手的被动端进入 CLOSE_WAIT */
            printf("  [fd=%d] 收到 FIN, 关闭连接\n", conn_fd);
            goto close_conn;
        }

        /* n < 0 */
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            /* 缓冲区读空了, ET 模式下的正常退出点 */
            goto done;
        }

        /* 其他错误 (ECONNRESET, ETIMEDOUT 等) */
        perror("read");
        goto close_conn;
    }

close_conn:
    close(conn_fd);
    /*
     * 注意: close(conn_fd) 会自动把 conn_fd 从 epoll 的 rbr 里移除。
     * 不需要显式调 epoll_ctl(EPOLL_CTL_DEL)。
     * 内核在 close 时遍历 fd 关联的所有 epoll 实例, 调用 ep_remove()。
     */
done:
    return;
}


/* ======================================================================
 * 处理 listen_fd 上的可读事件 (新的客户端连接)
 *
 * ET 模式下也要循环 accept, 直到返回 EAGAIN:
 *   高并发下 ACCEPT 队列可能瞬间积压多个连接,
 *   必须一次性全部 accept 光, 否则不会再有 EPOLLIN 通知。
 * ====================================================================== */
static void handle_accept(int epfd, int listen_fd)
{
    struct sockaddr_in client_addr;
    socklen_t addr_len;
    int conn_fd;

    while (1) {
        addr_len = sizeof(client_addr);
        conn_fd = accept(listen_fd, (struct sockaddr *)&client_addr, &addr_len);

        if (conn_fd < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                /* ACCEPT 队列取空了, ET 模式下的正常退出点 */
                break;
            }
            perror("accept");
            break;
        }

        /* 打印客户端信息 */
        char ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr.sin_addr, ip, sizeof(ip));
        printf("[fd=%d] 新连接: %s:%d\n",
               conn_fd, ip, ntohs(client_addr.sin_port));

        /* ---- 关键步: 把新连接注册到 epoll ---- */
        set_nonblocking(conn_fd);  /* ET 模式必须非阻塞 */

        struct epoll_event ev;
        ev.events   = EPOLLIN | EPOLLET;   /* 边沿触发: 有新数据到达才通知一次 */
        ev.data.fd  = conn_fd;              /* 把 fd 塞进 data, 事件返回时直接知道是谁 */
        if (epoll_ctl(epfd, EPOLL_CTL_ADD, conn_fd, &ev) < 0) {
            perror("epoll_ctl ADD conn_fd");
            close(conn_fd);
            continue;
        }

        /*
         * 此时内核里发生了什么:
         *
         * 1. 创建 epitem{fd=conn_fd, event=EPOLLIN|EPOLLET}
         *    插入 eventpoll.rbr (红黑树)
         *
         * 2. 在 conn_fd→sock→sk_wq 上注册回调:
         *    wait_queue_entry {
         *      .func    = ep_poll_callback
         *      .private = epitem(conn_fd)
         *    }
         *
         *    此后数据到达时, 内核遍历 sk_wq:
         *    → 调 ep_poll_callback → 挂 epitem 到 rdllist
         *    → ET 模式: epoll_wait 返回后摘掉 epitem
         *    → 不再重复报告, 直到下一次数据到达触发新回调
         */
    }
}


/* ======================================================================
 * 事件循环 — 单线程 Reactor 的核心
 *
 *      epoll_wait(epfd, events, MAX, -1);
 *      for (i < n) {
 *          if (fd == listen_fd)  handle_accept()
 *          else                  handle_client_read()
 *      }
 *
 *  就这么简单。整个服务器就是一个 while 循环,
 *  哪也不阻塞(除了 epoll_wait 本身)。
 * ====================================================================== */
int main()
{
    int listen_fd, epfd;
    struct epoll_event ev, events[MAX_EVENTS];

    /* ---- 准备 ---- */
    listen_fd = create_listen_socket();

    /* ---- epoll_create1() ---- */
    /*
     * epoll_create1(0) 等价于 epoll_create(1), 但:
     *   epoll_create1(EPOLL_CLOEXEC) → 自动设置 close-on-exec 标志,
     *   防止子进程意外继承 epoll fd (安全最佳实践)。
     *
     * 内核做了什么:
     *   1. 分配 struct eventpoll {rbr: 空红黑树, rdllist: 空链表, wq: 空队列}
     *   2. 分配一个 fd, 建立 fd → file → eventpoll 的映射
     *   3. epfd 本身也是一个 fd! 可以被 poll/select/另一个 epoll 监视
     */
    epfd = epoll_create1(0);
    if (epfd < 0) { perror("epoll_create1"); exit(EXIT_FAILURE); }
    printf("[4] epoll_create1() → epfd = %d\n", epfd);
    printf("    内核分配 struct eventpoll:\n");
    printf("      rbr:     空红黑树 (存被监视的 fd 全集)\n");
    printf("      rdllist: 空链表   (存就绪 fd 子集)\n");
    printf("      wq:      空队列   (存 epoll_wait 的线程)\n\n");

    /* ---- epoll_ctl(ADD, listen_fd) ---- */
    /*
     * 把 listen_fd 注册到 epoll。
     *
     * 内核做了什么:
     *   1. 创建 epitem{fd=listen_fd, event=EPOLLIN}
     *   2. 插入 eventpoll.rbr (红黑树)
     *   3. 在 listen_fd→sock→sk_wq 上挂 ep_poll_callback
     *
     * 之后三次握手完成的连接进入 ACCEPT 队列时:
     *   sock_def_readable() → wake_up(sk_wq)
     *   → ep_poll_callback → 挂 epitem 到 rdllist
     *   → wake_up(eventpoll.wq) → epoll_wait 返回
     */
    ev.events  = EPOLLIN;        /* 可读 = ACCEPT 队列非空 */
    ev.data.fd = listen_fd;      /* 事件返回时用 data.fd 区分是谁 */
    if (epoll_ctl(epfd, EPOLL_CTL_ADD, listen_fd, &ev) < 0) {
        perror("epoll_ctl ADD listen_fd");
        exit(EXIT_FAILURE);
    }
    printf("[5] epoll_ctl(ADD, listen_fd=%d, EPOLLIN)\n", listen_fd);
    printf("    在 listen_fd.sk_wq 上挂了 ep_poll_callback\n");
    printf("    此后内核会在三次握手完成后唤醒我们\n\n");

    /* ==================================================================
     * 主事件循环 — 单线程 Reactor
     *
     * 这是整个服务器的灵魂:
     *
     *   1. epoll_wait → 在 eventpoll.wq 上睡眠
     *      (不是在某个 socket 上睡, 而是在 epoll 实例上睡)
     *
     *   2. 任何一个 fd 有数据 → 回调唤醒我们
     *
     *   3. 遍历就绪事件, listen_fd → accept, 其他 → read/write
     *
     *   4. 回到 1
     *
     * 单线程 epoll 没有惊群 (wq 上就一个人)。
     * 零上下文切换 (除了系统调用)。
     * 零锁 (没有共享状态需要保护)。
     * ================================================================== */
    printf("═══════════════════════════════════════════\n");
    printf("进入事件循环 (单线程 Reactor)\n");
    printf("═══════════════════════════════════════════\n\n");

    while (1) {
        /*
         * epoll_wait() — 在 eventpoll.wq 上睡眠
         *
         * 参数:
         *   epfd     = epoll 实例
         *   events   = 出参, 内核把就绪事件拷到这里
         *   maxevents= 最多返回多少个事件
         *   timeout  = -1 (无限等待, 直到有事件)
         *
         * 内核逻辑 (简化):
         *   if (rdllist 为空) {
         *       挂线程到 eventpoll.wq → TASK_INTERRUPTIBLE → 调度走
         *   }
         *   // ... 被 ep_poll_callback 中的 wake_up 唤醒 ...
         *   遍历 rdllist, 拷贝事件到用户态 events[]
         *   ET 模式: 从 rdllist 摘掉 epitem
         *   返回就绪事件数量
         */
        int n = epoll_wait(epfd, events, MAX_EVENTS, -1);
        if (n < 0) {
            if (errno == EINTR)
                continue;  /* 被信号打断, 重试 */
            perror("epoll_wait");
            break;
        }

        for (int i = 0; i < n; i++) {
            int fd = events[i].data.fd;

            if (fd == listen_fd) {
                /*
                 * listen_fd 可读 → ACCEPT 队列非空 → 新连接来了
                 *
                 * 这里为什么 accept 不阻塞?
                 *   因为 epoll_wait 已经告诉我们 listen_fd 上有 EPOLLIN 事件。
                 *   这个事件的来源: 三次握手完成 → sock_def_readable()
                 *   → ep_poll_callback → rdllist → epoll_wait 返回。
                 *   所以 ACCEPT 队列里一定有连接, accept 不会阻塞。
                 */
                handle_accept(epfd, listen_fd);
            } else {
                /*
                 * conn_fd 可读 → sk_receive_queue 有数据
                 *
                 * 这里为什么 read 不阻塞?
                 *   同理, 事件来自 ep_poll_callback, 它是因为数据到达
                 *   sk_receive_queue 才被调用的。所以缓冲区里一定有数据。
                 *
                 * 但 ET 模式下必须循环读到 EAGAIN——
                 *   只能保证"至少有一次数据", 不能保证"只触发一次就够读完"。
                 */
                handle_client_read(fd);
            }
        }
    }

    close(listen_fd);
    close(epfd);
    return 0;
}
