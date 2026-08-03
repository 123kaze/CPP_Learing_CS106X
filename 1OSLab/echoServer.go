/*
 * echoServer.go — Go 单 goroutine-per-connection Echo Server
 *
 * 运行: go run echoServer.go
 * 测试: nc localhost 8080
 *
 * =====================================================================
 * 这段代码和你的 C epoll 版本的对应关系:
 *
 *   C epoll 版                            Go 版
 *   ──────────                            ─────
 *   epoll_create()                        runtime 启动时自动创建全局 epoll
 *   epoll_ctl(ADD, conn_fd)               遇到 EAGAIN 时 runtime 自动注册
 *   epoll_wait()                          一条后台 goroutine 在循环等待
 *   for each event: dispatch              不需要你 dispatch, 每个 goroutine
 *                                         独立处理自己的连接
 *
 * Go runtime 做了那三件事:
 *   1. socket() 返回的 fd 自动设成 O_NONBLOCK
 *   2. conn.Read() 返回 EAGAIN → runtime 自动 epoll_ctl(ADD) + 挂起 goroutine
 *   3. 数据到达 → 回调唤醒 goroutine → 放回 runqueue → 从 Read 返回
 * =====================================================================
 */

package main

import (
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"
)

/*
 * handleConn — 一个连接一个 goroutine
 *
 * 这个函数的写法是 "同步阻塞" 的——ReadString 看起来会卡住。
 * 但实际上:
 *   1. net.Conn 底层 fd 是 O_NONBLOCK 的
 *   2. 读不到数据时, runtime 把当前 goroutine 挂起, 把 fd 注册到 netpoller
 *   3. M (内核线程) 去跑另一个 goroutine — 完全不浪费
 *   4. 数据到达后, netpoller 把 goroutine 放回 runqueue
 *   5. 调度器选中 → goroutine 从 ReadString "醒来", 拿到数据
 *
 * 程序员视角: 一个连接一个独立函数, 逻辑简单线性。
 * runtime 视角: 背后在跑 epoll/kqueue, 和你手写的 C 代码一样。
 */
func handleConn(conn net.Conn) {
	defer conn.Close()

	// 每个 goroutine 初始栈只有 2KB
	// 对比: 内核线程栈固定 8MB
	buf := make([]byte, 4096)

	for {
		/*
		 * conn.Read(buf) 本质上是:
		 *   1. 非阻塞 read(fd) → 没数据返回 EAGAIN
		 *   2. runtime 挂起当前 goroutine (_Grunning → _Gwaiting)
		 *   3. runtime 自动 epoll_ctl(ADD, fd, EPOLLIN) 注册到 netpoller
		 *      → 插入 eventpoll.rbr (红黑树)
		 *      → 在 conn_fd.sk_wq 上挂 ep_poll_callback
		 *   4. M (内核线程) 去跑 runqueue 里下一个 goroutine
		 *
		 * 数据到达后:
		 *   5. sk_wq 回调触发 → epitem 挂到 rdllist
		 *   6. netpoller 后台线程 epoll_wait 返回 → 找到 goroutine
		 *   7. goroutine → _Grunnable → 放回 runqueue
		 *   8. 调度器选中 → 从 conn.Read 返回, 拿到数据
		 *
		 * 整个过程中 M (内核线程) 没有阻塞——去跑了其他 goroutine。
		 * 和你 C epoll 版本的 read()+epoll_wait 做的事情完全一样,
		 * 只是你再也不需要手写事件循环。
		 */
		n, err := conn.Read(buf)

		if err != nil {
			// n == 0 + io.EOF → 对端发了 FIN → 四次向挥手
			// 其他错误 → EAGAIN 已经被 runtime 过滤, 只返回真正的错误
			// runtime 自动把 fd 从 netpoller 移除 (epoll_ctl DEL)
			return
		}

		/*
		 * 写回 — 通常直接成功
		 *
		 * 底层是非阻塞 write, 如果发送缓冲区满了:
		 *   1. runtime 挂起 goroutine
		 *   2. 把 fd 注册到 netpoller with EPOLLOUT
		 *   3. 缓冲区腾出空间后, goroutine 被唤醒继续写
		 *
		 * 但 echo server 的响应很短, 几乎不会触发这个路径
		 */
		_, err = conn.Write(buf[:n])
		if err != nil {
			return
		}
	}
}

func main() {
	/*
	 * net.Listen("tcp", ":8080") 底层干了的事:
	 *
	 *   socket(AF_INET, SOCK_STREAM, 0) → fd
	 *   setsockopt(fd, SO_REUSEADDR)
	 *   fcntl(fd, O_NONBLOCK)          ← Go 自动设的
	 *   bind(fd, 0.0.0.0:8080)
	 *   listen(fd, backlog)
	 *
	 * 返回的 net.Listener 已经把 listen_fd 注册到了 netpoller。
	 * 不需要你手动 epoll_ctl(ADD, listen_fd)。
	 */
	ln, err := net.Listen("tcp", ":8080")
	if err != nil {
		log.Fatal(err)
	}
	defer ln.Close()

	fmt.Println("═══════════════════════════════════════════")
	fmt.Println("  Go Echo Server (goroutine-per-connection)")
	fmt.Println("═══════════════════════════════════════════")
	fmt.Println("  监听 :8080")
	fmt.Println()
	fmt.Println("  Go runtime 已经在底层:")
	fmt.Println("  ✓ 创建全局 netpoller (epoll/kqueue)")
	fmt.Println("  ✓ 把 listen_fd 设成 O_NONBLOCK")
	fmt.Println("  ✓ 把 listen_fd 注册到 netpoller")
	fmt.Println("  ✓ 每个 conn.Read() EAGAIN 时自动挂起/唤醒 goroutine")
	fmt.Println("═══════════════════════════════════════════")
	fmt.Println()

	// 优雅退出: Ctrl+C 时关闭 listener
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	/*
	 * 主事件循环 — 和你的 C epoll 版本的 while+epoll_wait 做的事一样
	 *
	 * 区别: 你不写 while+epoll_wait+for 循环 dispatch。
	 * Go runtime 在背景线程里跑 epoll_wait,
	 * 把就绪事件自动转化为 goroutine 的挂起/唤醒。
	 */
	go func() {
		<-sigCh
		fmt.Println("\n关闭服务器...")
		ln.Close()
		os.Exit(0)
	}()

	var connID int
	for {
		/*
		 * Accept() — Go 的 accept() 是非阻塞的
		 *
		 * 底层: listen_fd 已注册在 netpoller 里。
		 *       新连接到达 → epoll 回调 → 把 Accept 所在的 goroutine
		 *       从 _Gwaiting 唤醒放回 runqueue。
		 *       和你的 C epoll 版本 handle_accept() 做的事情一样,
		 *       只是你写的是显式的 epoll_wait + accept,
		 *       Go 把这个过程藏在了 Accept() 调用里。
		 */
		conn, err := ln.Accept()
		if err != nil {
			// listener 已关闭 (Ctrl+C)
			return
		}

		connID++
		fmt.Printf("[+] 新连接 #%d: %s\n", connID, conn.RemoteAddr())

		/*
		 * go handleConn(conn) 做了什么:
		 *
		 *   1. 分配 goroutine 结构体 + 2KB 初始栈 (纯用户态操作)
		 *   2. 初始化 goroutine → 放入当前 P 的 runqueue
		 *   3. 调度器下次选中时, goroutine 开始执行 handleConn
		 *   4. handleConn 里第一次 conn.Read() 时,
		 *      read 返回 EAGAIN → runtime 挂起 goroutine,
		 *      conn.fd 自动注册到 netpoller
		 *
		 * 对比:
		 *   内核线程: pthread_create → clone 系统调用 → 8MB 内核栈
		 *            → task_struct 分配 → 调度器初始化
		 *   goroutine: go func(){} → 2KB 栈 → 用戶态队列
		 *
		 *   创建开销差 2-3 个数量级。
		 */
		go handleConn(conn)
	}
}
