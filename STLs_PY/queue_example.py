"""
@file queue.py
@brief Python队列(queue)用法示例

队列是一种先进先出(FIFO)的数据结构，Python中可以使用queue.Queue、collections.deque或list实现
特点：
1. 先进先出：最先添加的元素最先被移除
2. 线程安全：queue.Queue是线程安全的，适合多线程环境
3. 阻塞操作：queue.Queue支持阻塞的put()和get()操作
4. 大小限制：可以设置队列的最大容量

常用实现方式：
1. queue.Queue：线程安全的队列，支持阻塞操作
2. collections.deque：双端队列，两端操作高效
3. list：简单但不高效（pop(0)是O(n)操作）
"""

import queue
from collections import deque
import threading
import time


def main():
    print("========== Python队列(queue)用法示例 ==========")

    # 1. 使用queue.Queue实现队列
    print("\n1. 使用queue.Queue实现队列:")

    # 创建队列
    q1 = queue.Queue()
    print(f"创建队列: {q1}")
    print(f"队列大小: {q1.qsize()} (初始为空)")

    # 入队操作
    q1.put("任务1")
    q1.put("任务2")
    q1.put("任务3")
    print(f"入队3个任务后队列大小: {q1.qsize()}")

    # 出队操作
    task = q1.get()
    print(f"出队任务: {task}, 队列大小: {q1.qsize()}")

    task = q1.get()
    print(f"出队任务: {task}, 队列大小: {q1.qsize()}")

    # 标记任务完成
    q1.task_done()
    q1.task_done()

    # 等待所有任务完成
    q1.join()
    print("所有任务已完成")

    # 2. 使用collections.deque实现队列
    print("\n2. 使用collections.deque实现队列:")

    dq = deque()
    dq.append("客户1")
    dq.append("客户2")
    dq.append("客户3")
    print(f"入队后队列: {dq}, 大小: {len(dq)}")

    # 出队
    customer = dq.popleft()
    print(f"服务客户: {customer}, 剩余队列: {dq}")

    customer = dq.popleft()
    print(f"服务客户: {customer}, 剩余队列: {dq}")

    # 3. 队列的基本操作
    print("\n3. 队列的基本操作:")

    q2 = queue.Queue(maxsize=3)  # 设置最大容量
    print(f"创建容量为3的队列")

    # 入队（如果队列满会阻塞）
    q2.put("A", block=False)  # 非阻塞模式
    q2.put("B", block=False)
    q2.put("C", block=False)
    print(f"入队3个元素后队列大小: {q2.qsize()}")

    # 尝试入队（队列已满）
    try:
        q2.put("D", block=False, timeout=1)
    except queue.Full:
        print("队列已满，无法入队")

    # 查看队列是否为空/满
    print(f"队列是否为空: {q2.empty()}")
    print(f"队列是否已满: {q2.full()}")

    # 获取队列中的所有元素（不弹出）
    print("队列中的元素:")
    while not q2.empty():
        item = q2.get()
        print(f"  {item}")
        q2.task_done()

    # 4. 阻塞队列操作
    print("\n4. 阻塞队列操作:")

    def producer(q, items):
        """生产者线程"""
        for item in items:
            print(f"生产者: 生产 {item}")
            q.put(item)
            time.sleep(0.1)
        q.put(None)  # 结束信号

    def consumer(q):
        """消费者线程"""
        while True:
            item = q.get()
            if item is None:  # 结束信号
                q.task_done()
                break
            print(f"消费者: 消费 {item}")
            time.sleep(0.2)
            q.task_done()

    # 创建队列
    q3 = queue.Queue()

    # 创建生产者和消费者线程
    producer_thread = threading.Thread(
        target=producer, args=(q3, ["苹果", "香蕉", "橙子", "葡萄"])
    )
    consumer_thread = threading.Thread(target=consumer, args=(q3,))

    print("生产者-消费者示例:")
    producer_thread.start()
    consumer_thread.start()

    # 等待线程完成
    producer_thread.join()
    consumer_thread.join()
    q3.join()
    print("生产者-消费者示例完成")

    # 5. 优先级队列
    print("\n5. 优先级队列:")

    pq = queue.PriorityQueue()

    # 入队（优先级，数据）
    pq.put((3, "低优先级任务"))
    pq.put((1, "高优先级任务"))
    pq.put((2, "中优先级任务"))

    print("优先级队列中的任务（按优先级顺序）:")
    while not pq.empty():
        priority, task = pq.get()
        print(f"  优先级{priority}: {task}")
        pq.task_done()

    # 6. LIFO队列（栈）
    print("\n6. LIFO队列（栈）:")

    lifo_q = queue.LifoQueue()

    lifo_q.put("第一层")
    lifo_q.put("第二层")
    lifo_q.put("第三层")

    print("LIFO队列（后进先出）:")
    while not lifo_q.empty():
        item = lifo_q.get()
        print(f"  弹出: {item}")
        lifo_q.task_done()

    # 7. 实际应用场景
    print("\n7. 实际应用场景:")

    # 场景1：任务调度系统
    print("场景1: 任务调度系统")

    class TaskScheduler:
        def __init__(self, max_workers=2):
            self.task_queue = queue.Queue()
            self.max_workers = max_workers
            self.workers = []

        def add_task(self, task):
            """添加任务"""
            self.task_queue.put(task)
            print(f"添加任务: {task}")

        def worker(self, worker_id):
            """工作线程"""
            while True:
                try:
                    task = self.task_queue.get(timeout=1)
                    if task is None:  # 结束信号
                        self.task_queue.task_done()
                        break

                    print(f"工作者{worker_id}: 执行任务 '{task}'")
                    time.sleep(0.5)  # 模拟任务执行
                    print(f"工作者{worker_id}: 完成任务 '{task}'")
                    self.task_queue.task_done()
                except queue.Empty:
                    continue

        def start(self):
            """启动工作线程"""
            for i in range(self.max_workers):
                worker_thread = threading.Thread(target=self.worker, args=(i + 1,))
                worker_thread.daemon = True
                worker_thread.start()
                self.workers.append(worker_thread)

        def wait_completion(self):
            """等待所有任务完成"""
            self.task_queue.join()
            print("所有任务已完成")

    scheduler = TaskScheduler(max_workers=2)
    scheduler.start()

    # 添加任务
    for i in range(5):
        scheduler.add_task(f"任务{i+1}")

    # 等待任务完成
    scheduler.wait_completion()

    # 场景2：消息队列
    print("\n场景2: 消息队列")

    class MessageQueue:
        def __init__(self):
            self.queue = queue.Queue()
            self.subscribers = []

        def publish(self, message):
            """发布消息"""
            print(f"发布消息: {message}")
            self.queue.put(message)

        def subscribe(self, subscriber_name):
            """订阅消息"""

            def subscriber():
                while True:
                    message = self.queue.get()
                    if message == "EXIT":
                        self.queue.task_done()
                        break
                    print(f"{subscriber_name} 收到消息: {message}")
                    time.sleep(0.1)
                    self.queue.task_done()

            thread = threading.Thread(target=subscriber)
            thread.daemon = True
            thread.start()
            self.subscribers.append(thread)

        def stop(self):
            """停止消息队列"""
            self.queue.put("EXIT")
            self.queue.join()

    mq = MessageQueue()
    mq.subscribe("订阅者A")
    mq.subscribe("订阅者B")

    # 发布消息
    for i in range(3):
        mq.publish(f"消息{i+1}")

    time.sleep(0.5)
    mq.stop()

    # 场景3：打印任务队列
    print("\n场景3: 打印任务队列")

    print_queue = queue.Queue()

    def printer_worker():
        """打印机工作线程"""
        while True:
            document = print_queue.get()
            if document is None:
                print_queue.task_done()
                break

            print(f"正在打印: {document}")
            time.sleep(0.3)  # 模拟打印时间
            print(f"完成打印: {document}")
            print_queue.task_done()

    # 启动打印机线程
    printer_thread = threading.Thread(target=printer_worker)
    printer_thread.start()

    # 添加打印任务
    documents = ["报告1.pdf", "报告2.pdf", "简历.docx", "照片.jpg"]
    for doc in documents:
        print_queue.put(doc)
        print(f"添加到打印队列: {doc}")

    # 等待所有打印任务完成
    print_queue.join()

    # 停止打印机线程
    print_queue.put(None)
    printer_thread.join()

    # 场景4：Web请求队列
    print("\n场景4: Web请求队列（简化版）")

    class RequestQueue:
        def __init__(self, max_concurrent=3):
            self.queue = queue.Queue()
            self.max_concurrent = max_concurrent
            self.active_requests = 0

        def add_request(self, url):
            """添加请求"""
            self.queue.put(url)
            print(f"添加请求: {url}")

        def process_requests(self):
            """处理请求"""
            while not self.queue.empty():
                if self.active_requests < self.max_concurrent:
                    url = self.queue.get()
                    self.active_requests += 1

                    # 模拟处理请求
                    print(f"开始处理: {url}")
                    time.sleep(0.2)  # 模拟网络延迟
                    print(f"完成处理: {url}")

                    self.active_requests -= 1
                    self.queue.task_done()
                else:
                    time.sleep(0.1)  # 等待有空闲

    request_queue = RequestQueue(max_concurrent=2)

    # 添加请求
    urls = [
        "https://api.example.com/data1",
        "https://api.example.com/data2",
        "https://api.example.com/data3",
        "https://api.example.com/data4",
        "https://api.example.com/data5",
    ]

    for url in urls:
        request_queue.add_request(url)

    # 处理请求
    request_queue.process_requests()

    # 8. 性能提示
    print("\n8. 性能提示:")
    print("1. queue.Queue是线程安全的，适合多线程环境")
    print("2. collections.deque的popleft()是O(1)，比list的pop(0)的O(n)更高效")
    print("3. 对于单线程应用，使用collections.deque比queue.Queue更高效")
    print("4. 设置合适的队列容量可以防止内存溢出")
    print("5. 使用阻塞操作时要注意死锁问题")
    print("6. PriorityQueue内部使用堆实现，入队出队是O(log n)")
    print("7. 对于大量数据，考虑使用专门的消息队列系统（如RabbitMQ、Kafka）")

    # 9. 常见问题
    print("\n9. 常见问题:")

    # 问题1：队列死锁
    print("问题1: 队列死锁")
    deadlock_q = queue.Queue(maxsize=1)
    deadlock_q.put("item1")

    # 以下代码会导致死锁（队列已满，没有消费者）
    # deadlock_q.put("item2", block=True)  # 会一直阻塞

    # 解决方案：使用非阻塞模式或设置超时
    try:
        deadlock_q.put("item2", block=False)
    except queue.Full:
        print("  队列已满，无法添加新项目")

    # 问题2：忘记调用task_done()
    print("\n问题2: 忘记调用task_done()")
    q_without_done = queue.Queue()
    q_without_done.put("task1")
    q_without_done.get()
    # 忘记调用 q_without_done.task_done()
    # 这会导致 q_without_done.join() 永远阻塞

    # 正确的做法
    q_correct = queue.Queue()
    q_correct.put("task1")
    item = q_correct.get()
    q_correct.task_done()  # 必须调用
    print("  正确处理: 调用task_done()")

    # 问题3：队列大小监控
    print("\n问题3: 队列大小监控")
    monitored_q = queue.Queue(maxsize=10)

    # 监控队列大小
    for i in range(15):
        try:
            monitored_q.put(f"item{i}", block=False)
            print(f"  添加item{i}，队列大小: {monitored_q.qsize()}")
        except queue.Full:
            print(f"  队列已满，无法添加item{i}")
            break

    print("\n========== Python队列示例结束 ==========")


if __name__ == "__main__":
    main()
