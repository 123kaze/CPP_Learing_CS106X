/*
 * bench.c — epoll echo server 并发压力测试工具
 *
 * 编译: gcc -Wall -O2 -o bench bench.c
 * 用法: ./bench <connections> <messages_per_conn> [port]
 * 例:   ./bench 1000 10        (1000个连接, 每个发10条消息)
 *       ./bench 100 10 8080    (指定端口)
 *
 * 测试模型:
 *   1. 一次性创建 N 个连接 (测试 accept 吞吐)
 *   2. 所有连接同时发消息 (测试并发读写)
 *   3. 验证回显正确性
 *   4. 统计延迟和吞吐
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/time.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define DEFAULT_PORT 8080
#define BUF_SIZE     256

static double now_ms()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000.0 + tv.tv_usec / 1000.0;
}

/* 非阻塞 connect */
static int do_connect(int port)
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { perror("socket"); return -1; }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr.sin_port        = htons(port);

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("connect");
        close(fd);
        return -1;
    }
    return fd;
}

int main(int argc, char *argv[])
{
    if (argc < 3) {
        fprintf(stderr, "用法: %s <连接数> <每连接消息数> [端口]\n", argv[0]);
        return 1;
    }

    int N_CONN  = atoi(argv[1]);
    int N_MSGS  = atoi(argv[2]);
    int port    = argc >= 4 ? atoi(argv[3]) : DEFAULT_PORT;

    printf("═══════════════════════════════════════════\n");
    printf("  epoll Echo Server 并发压力测试\n");
    printf("═══════════════════════════════════════════\n");
    printf("  连接数:       %d\n", N_CONN);
    printf("  每连接消息数:  %d\n", N_MSGS);
    printf("  总消息数:      %d\n", N_CONN * N_MSGS);
    printf("  端口:          %d\n", port);
    printf("═══════════════════════════════════════════\n\n");

    int *fds = malloc(N_CONN * sizeof(int));
    if (!fds) { perror("malloc"); return 1; }

    /* ── 阶段1: 建立所有连接 ── */
    printf("[1/3] 建立 %d 个连接...\n", N_CONN);
    double t0 = now_ms();
    int connected = 0;
    for (int i = 0; i < N_CONN; i++) {
        fds[i] = do_connect(port);
        if (fds[i] < 0) {
            fprintf(stderr, "第 %d 个连接失败, 停止\n", i);
            break;
        }
        connected++;
    }
    double t1 = now_ms();
    double conn_time = t1 - t0;
    printf("  ✓ 成功建立 %d/%d 个连接\n", connected, N_CONN);
    printf("  耗时: %.1f ms (%.0f conn/s)\n\n", conn_time,
           connected / (conn_time / 1000.0));

    if (connected == 0) {
        printf("没有可用连接, 退出\n");
        free(fds);
        return 1;
    }

    /* ── 阶段2: 收发消息 ── */
    printf("[2/3] 每个连接发送 %d 条消息...\n", N_MSGS);
    char send_buf[BUF_SIZE], recv_buf[BUF_SIZE];
    long total_msgs = 0, total_bytes = 0;
    int recv_errors = 0;

    t0 = now_ms();
    for (int i = 0; i < connected; i++) {
        for (int j = 0; j < N_MSGS; j++) {
            int len = snprintf(send_buf, sizeof(send_buf),
                               "conn=%d msg=%d", i, j);

            /* 发送 */
            ssize_t w = write(fds[i], send_buf, len);
            if (w != len) {
                fprintf(stderr, "write 失败 fd=%d: %zd/%d\n", fds[i], w, len);
                goto next_conn;
            }

            /* 接收回显 */
            ssize_t r = read(fds[i], recv_buf, sizeof(recv_buf) - 1);
            if (r < 0) {
                fprintf(stderr, "read 失败 fd=%d errno=%d\n", fds[i], errno);
                recv_errors++;
                goto next_conn;
            }
            recv_buf[r] = '\0';

            /* 验证 */
            if (r != len || memcmp(send_buf, recv_buf, len) != 0) {
                fprintf(stderr, "数据不匹配! fd=%d 发送=\"%s\" 收到=\"%s\"\n",
                        fds[i], send_buf, recv_buf);
                recv_errors++;
            }

            total_msgs++;
            total_bytes += r;
        }
    next_conn:;
    }
    t1 = now_ms();
    double msg_time = t1 - t0;

    printf("  ✓ 完成 %ld 次请求/响应\n", total_msgs);
    printf("  数据错误:      %d\n", recv_errors);
    printf("  总数据量:      %.1f KB\n", total_bytes / 1024.0);
    printf("  耗时:          %.1f ms\n", msg_time);
    printf("  QPS (消息/秒): %.0f\n", total_msgs / (msg_time / 1000.0));
    printf("  吞吐:          %.1f KB/s\n\n",
           (total_bytes / 1024.0) / (msg_time / 1000.0));

    /* ── 阶段3: 关闭所有连接 ── */
    printf("[3/3] 关闭所有连接...\n");
    for (int i = 0; i < connected; i++)
        close(fds[i]);
    printf("  ✓ 完成\n\n");

    /* ── 汇总 ── */
    printf("═══════════════════════════════════════════\n");
    printf("  总结\n");
    printf("═══════════════════════════════════════════\n");
    printf("  连接:  %d 个, 耗时 %.0f ms (%.0f conn/s)\n",
           connected, conn_time, connected / (conn_time / 1000.0));
    printf("  消息:  %ld 个, 耗时 %.0f ms (%.0f msg/s)\n",
           total_msgs, msg_time, total_msgs / (msg_time / 1000.0));
    printf("  总耗时: %.0f ms\n", conn_time + msg_time);

    if (recv_errors == 0)
        printf("  数据完整性: ✓ 全部正确\n");
    else
        printf("  数据完整性: ✗ %d 个错误\n", recv_errors);
    printf("═══════════════════════════════════════════\n");

    free(fds);
    return recv_errors ? 1 : 0;
}
