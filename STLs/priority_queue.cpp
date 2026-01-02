/**
 * @file priority_queue.cpp
 * @brief priority_queue容器用法示例
 * 
 * priority_queue是C++标准模板库(STL)中的优先队列容器适配器
 * 特点：
 * 1. 优先级队列：元素按优先级顺序出队，优先级最高的元素最先出队
 * 2. 容器适配器：基于其他容器实现（默认vector）
 * 3. 堆结构：内部使用堆数据结构维护元素优先级
 * 4. 自动排序：插入元素时自动维护堆性质
 * 
 * 常用操作时间复杂度：
 * - 插入元素(push)：O(log n)
 * - 删除最高优先级元素(pop)：O(log n)
 * - 访问最高优先级元素(top)：O(1)
 * - 判断空(empty)：O(1)
 * - 获取大小(size)：O(1)
 */

#include <iostream>
#include <queue>
#include <vector>
#include <functional>

using namespace std;

int main() {
    cout << "========== priority_queue容器用法示例 ==========" << endl;
    
    // 1. 创建priority_queue
    cout << "\n1. 创建priority_queue:" << endl;
    
    // 默认创建最大堆（大顶堆）
    priority_queue<int> pq1;
    cout << "默认priority_queue（最大堆）大小: " << pq1.size() << endl;
    
    // 创建最小堆（小顶堆）
    priority_queue<int, vector<int>, greater<int>> pq2;
    cout << "最小堆priority_queue大小: " << pq2.size() << endl;
    
    // 使用自定义比较函数
    auto cmp = [](int left, int right) { return left > right; };
    priority_queue<int, vector<int>, decltype(cmp)> pq3(cmp);
    cout << "自定义比较函数priority_queue大小: " << pq3.size() << endl;
    
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;
    
    // 插入元素
    pq1.push(30);
    pq1.push(10);
    pq1.push(50);
    pq1.push(20);
    pq1.push(40);
    
    cout << "插入元素后pq1大小: " << pq1.size() << endl;
    cout << "堆顶元素（最大值）: " << pq1.top() << endl;
    
    // 删除堆顶元素
    pq1.pop();
    cout << "删除堆顶元素后堆顶元素: " << pq1.top() << endl;
    cout << "删除后pq1大小: " << pq1.size() << endl;
    
    // 3. 最大堆 vs 最小堆
    cout << "\n3. 最大堆 vs 最小堆:" << endl;
    
    // 最大堆示例
    priority_queue<int> max_heap;
    for (int i = 1; i <= 5; i++) {
        max_heap.push(i * 10);
    }
    
    cout << "最大堆元素出队顺序: ";
    while (!max_heap.empty()) {
        cout << max_heap.top() << " ";
        max_heap.pop();
    }
    cout << endl;
    
    // 最小堆示例
    priority_queue<int, vector<int>, greater<int>> min_heap;
    for (int i = 1; i <= 5; i++) {
        min_heap.push(i * 10);
    }
    
    cout << "最小堆元素出队顺序: ";
    while (!min_heap.empty()) {
        cout << min_heap.top() << " ";
        min_heap.pop();
    }
    cout << endl;
    
    // 4. 遍历priority_queue（注意：priority_queue不支持直接遍历）
    cout << "\n4. 遍历priority_queue:" << endl;
    cout << "priority_queue不支持直接遍历，需要借助临时priority_queue" << endl;
    
    priority_queue<int> temp_pq = pq1; // 拷贝复制
    cout << "priority_queue元素（按优先级顺序）: ";
    while (!temp_pq.empty()) {
        cout << temp_pq.top() << " ";
        temp_pq.pop();
    }
    cout << endl;
    
    // 5. 实际应用场景
    cout << "\n5. 实际应用场景:" << endl;
    
    // 场景1：Top K问题
    cout << "场景1: Top K问题（找出最大的K个元素）" << endl;
    
    vector<int> nums = {3, 2, 1, 5, 6, 4};
    int k = 3;
    
    // 使用最小堆找最大的K个元素
    priority_queue<int, vector<int>, greater<int>> topk_heap;
    
    for (int num : nums) {
        topk_heap.push(num);
        if (topk_heap.size() > k) {
            topk_heap.pop();  // 移除最小的元素
        }
    }
    
    cout << "数组: ";
    for (int num : nums) cout << num << " ";
    cout << endl;
    cout << "最大的" << k << "个元素: ";
    while (!topk_heap.empty()) {
        cout << topk_heap.top() << " ";
        topk_heap.pop();
    }
    cout << endl;
    
    // 场景2：合并K个有序链表
    cout << "\n场景2: 合并K个有序链表（模拟）" << endl;
    
    // 模拟K个有序数组
    vector<vector<int>> sorted_arrays = {
        {1, 4, 7},
        {2, 5, 8},
        {3, 6, 9}
    };
    
    // 使用最小堆合并
    struct Node {
        int value;
        int array_idx;
        int element_idx;
        
        bool operator>(const Node& other) const {
            return value > other.value;
        } // 小顶堆比较规则
    };
    
    priority_queue<Node, vector<Node>, greater<Node>> merge_heap;
    
    // 初始化堆，放入每个数组的第一个元素
    for (int i = 0; i < sorted_arrays.size(); i++) {
        if (!sorted_arrays[i].empty()) {
            merge_heap.push({sorted_arrays[i][0], i, 0});
            cout << sorted_arrays[i][0] << i<<0 <<" ";
        }
    }
    
    cout << "合并后的有序序列: ";
    while (!merge_heap.empty()) {
        Node current = merge_heap.top();
        merge_heap.pop();
        
        cout << current.value << " ";
        
        // 将当前数组的下一个元素加入堆
        int next_idx = current.element_idx + 1;
        if (next_idx < sorted_arrays[current.array_idx].size()) {
            merge_heap.push({sorted_arrays[current.array_idx][next_idx], 
                            current.array_idx, next_idx});
        }
    }
    cout << endl;
    
    // 场景3：任务调度（按优先级）
    cout << "\n场景3: 任务调度（按优先级）" << endl;
    
    struct Task {
        string name;
        int priority;  // 数字越小优先级越高
        
        bool operator<(const Task& other) const {
            return priority > other.priority;  // 最小堆
        }
    };
    
    priority_queue<Task> task_pq;
    
    task_pq.push({"系统任务", 1});
    task_pq.push({"用户任务", 3});
    task_pq.push({"紧急任务", 1});
    task_pq.push({"普通任务", 5});
    task_pq.push({"重要任务", 2});
    
    cout << "任务执行顺序（优先级从高到低）:" << endl;
    while (!task_pq.empty()) {
        Task task = task_pq.top();
        task_pq.pop();
        cout << "执行任务: " << task.name 
             << " (优先级: " << task.priority << ")" << endl;
    }
    
    // 6. 自定义比较函数
    cout << "\n6. 自定义比较函数:" << endl;
    
    // 自定义数据结构
    struct Point {
        int x, y;
        int distance() const { return x*x + y*y; }
    };
    
    // 按距离比较
    auto point_cmp = [](const Point& a, const Point& b) {
        return a.distance() < b.distance();  // 最大堆，距离大的优先级高
    };
    
    priority_queue<Point, vector<Point>, decltype(point_cmp)> point_pq(point_cmp);
    
    point_pq.push({1, 1});
    point_pq.push({3, 4});
    point_pq.push({0, 0});
    point_pq.push({2, 2});
    
    cout << "点按距离从大到小排序: ";
    while (!point_pq.empty()) {
        Point p = point_pq.top();
        point_pq.pop();
        cout << "(" << p.x << "," << p.y << ")[距离=" << p.distance() << "] ";
    }
    cout << endl;
    
    // 7. 性能提示
    cout << "\n7. 性能提示:" << endl;
    cout << "1. priority_queue基于堆实现，插入和删除操作都是O(log n)" << endl;
    cout << "2. 默认使用vector作为底层容器，也可以使用deque" << endl;
    cout << "3. 如果需要频繁访问中间元素，不要使用priority_queue" << endl;
    cout << "4. priority_queue的pop()不返回元素，需要先top()再pop()" << endl;
    cout << "5. 注意priority_queue的empty()判断，避免在空队列上调用top()或pop()" << endl;
    cout << "6. 自定义比较函数时，注意比较逻辑的方向（最大堆 vs 最小堆）" << endl;
    
    // 8. 与sort()的比较
    cout << "\n8. 与sort()的比较:" << endl;
    cout << "1. sort()一次性排序所有元素，时间复杂度O(n log n)" << endl;
    cout << "2. priority_queue维护动态排序，每次操作O(log n)" << endl;
    cout << "3. 如果需要动态添加元素并保持排序，使用priority_queue" << endl;
    cout << "4. 如果只需要一次性排序，使用sort()更高效" << endl;
    
    // 9. 底层容器选择
    cout << "\n9. 底层容器选择:" << endl;
    cout << "1. 默认使用vector: 内存连续，缓存友好，性能最好" << endl;
    cout << "2. 可以使用deque: 支持快速的头尾操作，但内存不连续" << endl;
    cout << "3. 不能使用list: list不支持随机访问，不符合堆的要求" << endl;
    cout << "4. 选择建议: 大多数情况下使用默认vector即可" << endl;
    
    cout << "\n========== priority_queue示例结束 ==========" << endl;
    
    return 0;
}
