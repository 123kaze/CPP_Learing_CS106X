/**
 * @file queue.cpp
 * @brief queue容器用法示例
 *
 * queue是C++标准模板库(STL)中的队列容器适配器
 * 特点：
 * 1. 先进先出(FIFO)：最先插入的元素最先被删除
 * 2. 容器适配器：基于其他容器实现（默认deque）
 * 3. 限制访问：只能访问队首和队尾元素
 * 4. 简单高效：操作简单，性能高效
 *
 * 常用操作时间复杂度：
 * - 入队(push)：O(1)
 * - 出队(pop)：O(1)
 * - 访问队首(front)：O(1)
 * - 访问队尾(back)：O(1)
 * - 判断空(empty)：O(1)
 * - 获取大小(size)：O(1)
 */

#include <deque>
#include <iostream>
#include <list>
#include <queue>
#include <vector>

using namespace std;

int main()
{
    cout << "========== queue容器用法示例 ==========" << endl;

    // 1. 创建queue
    cout << "\n1. 创建queue:" << endl;

    // 默认使用deque作为底层容器
    queue<int> q1;
    cout << "空queue大小: " << q1.size() << endl;

    // 使用list作为底层容器
    queue<int, list<int>> q2;
    cout << "使用list的queue大小: " << q2.size() << endl;

    // 使用deque作为底层容器（显式指定）
    queue<int, deque<int>> q3;
    cout << "使用deque的queue大小: " << q3.size() << endl;
    // 使用vector作为底层容器
    queue<int, vector<int>> q4;
    cout << "使用vector的queue大小: " << q4.size() << endl;
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;

    // 入队操作
    q1.push(10);
    q1.push(20);
    q1.push(30);
    q1.push(40);
    q1.push(50);

    cout << "入队5个元素后queue大小: " << q1.size() << endl;
    cout << "队首元素: " << q1.front() << endl;
    cout << "队尾元素: " << q1.back() << endl;

    // 出队操作
    q1.pop();
    cout << "出队后队首元素: " << q1.front() << endl;
    cout << "出队后queue大小: " << q1.size() << endl;
    cout << "队尾元素: " << q1.back() << endl;

    // 3. 遍历queue（注意：queue不支持直接遍历）
    cout << "\n3. 遍历queue:" << endl;
    cout << "queue不支持直接遍历，需要借助临时queue" << endl;

    queue<int> temp_q = q1;  // 复制拷贝
    cout << "queue元素（从队首到队尾）: ";
    while (!temp_q.empty())
    {
        cout << temp_q.front() << " ";
        temp_q.pop();
    }
    cout << endl;

    // 4. 判断空和获取大小
    cout << "\n4. 判断空和获取大小:" << endl;

    cout << "q1是否为空: " << (q1.empty() ? "是" : "否") << endl;
    cout << "q1大小: " << q1.size() << endl;

    // 清空queue
    while (!q1.empty())
    {
        q1.pop();
    }
    cout << "清空后q1是否为空: " << (q1.empty() ? "是" : "否") << endl;

    // 5. 实际应用场景
    cout << "\n5. 实际应用场景:" << endl;

    // 场景1：广度优先搜索(BFS)
    cout << "场景1: 广度优先搜索(BFS)" << endl;

    // 模拟图的邻接表
    vector<vector<int>> graph = {
        {1, 2},     // 节点0的邻居
        {0, 3, 4},  // 节点1的邻居
        {0, 5},     // 节点2的邻居
        {1},        // 节点3的邻居
        {1},        // 节点4的邻居
        {2}         // 节点5的邻居
    };

    vector<bool> visited(6, false);
    queue<int> bfs_queue;

    // 从节点0开始BFS
    bfs_queue.push(0);
    visited[0] = true;

    cout << "BFS遍历顺序: ";
    while (!bfs_queue.empty())
    {
        int current = bfs_queue.front();
        bfs_queue.pop();
        cout << current << " ";

        for (int neighbor : graph[current])
        {
            if (!visited[neighbor])
            {
                visited[neighbor] = true;
                bfs_queue.push(neighbor);
            }
        }
    }
    cout << endl;

    // 场景2：任务调度
    cout << "\n场景2: 任务调度" << endl;

    struct Task
    {
        string name;
        int priority;
        int duration;
    };

    queue<Task> task_queue;

    // 添加任务
    task_queue.push({"任务A", 1, 5});
    task_queue.push({"任务B", 2, 3});
    task_queue.push({"任务C", 1, 4});
    task_queue.push({"任务D", 3, 2});

    cout << "任务执行顺序:" << endl;
    int current_time = 0;
    while (!task_queue.empty())
    {
        Task task = task_queue.front();
        task_queue.pop();

        cout << "时间 " << current_time << "-" << current_time + task.duration << ": 执行"
             << task.name << " (优先级:" << task.priority << ", 耗时:" << task.duration << ")"
             << endl;

        current_time += task.duration;
    }

    // 场景3：消息队列
    cout << "\n场景3: 消息队列" << endl;

    queue<string> message_queue;

    // 生产者添加消息
    message_queue.push("用户登录");
    message_queue.push("订单创建");
    message_queue.push("支付成功");
    message_queue.push("物流发货");

    // 消费者处理消息
    cout << "处理消息:" << endl;
    while (!message_queue.empty())
    {
        string message = message_queue.front();
        message_queue.pop();
        cout << "处理消息: " << message << endl;
    }

    // 6. 不同底层容器的性能比较
    cout << "\n6. 不同底层容器的性能比较:" << endl;

    cout << "1. 默认使用deque: 综合性能最好，支持快速的头尾操作" << endl;
    cout << "2. 使用list: 每个操作都是O(1)，但内存开销大，缓存不友好" << endl;
    cout << "3. 不能使用vector: vector不支持O(1)的头部删除操作" << endl;
    cout << "4. 选择建议: 大多数情况下使用默认deque即可" << endl;

    // 7. 特殊队列类型
    cout << "\n7. 特殊队列类型:" << endl;

    // 双端队列（deque）可以作为queue使用
    deque<int> dq = {1, 2, 3, 4, 5};
    queue<int> q_from_deque(dq);  // 使用deque初始化queue

    cout << "从deque初始化的queue大小: " << q_from_deque.size() << endl;
    cout << "队首元素: " << q_from_deque.front() << endl;

    // 循环队列模拟
    cout << "\n循环队列模拟:" << endl;
    const int CIRCULAR_SIZE = 5;
    int circular_queue[CIRCULAR_SIZE];
    int front = 0, rear = 0, count = 0;

    auto enqueue_circular = [&](int value)
    {
        if (count < CIRCULAR_SIZE)
        {
            circular_queue[rear] = value;
            rear = (rear + 1) % CIRCULAR_SIZE;
            count++;
            return true;
        }
        return false;
    };

    auto dequeue_circular = [&]()
    {
        if (count > 0)
        {
            int value = circular_queue[front];
            front = (front + 1) % CIRCULAR_SIZE;
            count--;
            return value;
        }
        return -1;
    };

    // 测试循环队列
    for (int i = 1; i <= 6; i++)
    {
        if (enqueue_circular(i * 10))
        {
            cout << "入队: " << i * 10 << endl;
        }
        else
        {
            cout << "队列已满，无法入队: " << i * 10 << endl;
        }
    }

    cout << "出队: " << dequeue_circular() << endl;
    cout << "出队: " << dequeue_circular() << endl;

    // 8. 性能提示
    cout << "\n8. 性能提示:" << endl;
    cout << "1. queue是容器适配器，不是容器，它基于其他容器实现" << endl;
    cout << "2. 如果需要频繁访问中间元素，不要使用queue" << endl;
    cout << "3. queue的pop()不返回元素，需要先front()再pop()" << endl;
    cout << "4. 注意queue的empty()判断，避免在空队列上调用front()或pop()" << endl;
    cout << "5. 根据应用场景选择合适的底层容器" << endl;
    cout << "6. 对于需要优先级调度的场景，考虑使用priority_queue" << endl;

    // 9. queue与deque的区别
    cout << "\n9. queue与deque的区别:" << endl;
    cout << "1. queue是容器适配器，deque是容器" << endl;
    cout << "2. queue只支持FIFO操作，deque支持双端操作" << endl;
    cout << "3. queue的接口更简单，deque的接口更丰富" << endl;
    cout << "4. queue基于deque实现，但限制了访问方式" << endl;

    cout << "\n========== queue示例结束 ==========" << endl;

    return 0;
}
