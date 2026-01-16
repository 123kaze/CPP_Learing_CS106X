/**
 * @file deque.cpp
 * @brief deque容器用法示例
 *
 * deque（双端队列）是C++标准模板库(STL)中的双端队列容器
 * 特点：
 * 1. 双端操作：可以在头部和尾部高效地插入/删除元素
 * 2. 随机访问：支持O(1)时间的随机访问
 * 3. 分段连续：内部由多个连续内存块组成，对外表现为连续
 * 4. 动态扩容：自动管理内存，可动态调整大小
 *
 * 常用操作时间复杂度：
 * - 头部/尾部插入/删除：O(1)
 * - 中间插入/删除：O(n)
 * - 随机访问：O(1)
 * - 查找：O(n)
 */

#include <algorithm>
#include <deque>
#include <iostream>
#include <vector>

using namespace std;

int main()
{
    cout << "========== deque容器用法示例 ==========" << endl;

    // 1. 创建和初始化deque
    cout << "\n1. 创建和初始化deque:" << endl;

    // 空deque
    deque<int> dq1;
    cout << "空deque大小: " << dq1.size() << endl;

    // 指定大小和初始值
    deque<int> dq2(5, 10);  // 5个元素，每个都是10
    cout << "dq2: ";
    for (int num : dq2) cout << num << " ";
    cout << endl;

    // 使用初始化列表
    deque<int> dq3 = {1, 2, 3, 4, 5};
    cout << "dq3: ";
    for (int num : dq3) cout << num << " ";
    cout << endl;

    // 从数组初始化
    int arr[] = {6, 7, 8, 9, 10};  // arr实际上是一个地址指针
    deque<int> dq4(arr, arr + 5);
    cout << "dq4: ";
    for (int num : dq4) cout << num << " ";
    cout << endl;

    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;

    // 双端添加元素
    dq1.push_back(100);  // 尾部添加
    dq1.push_front(50);  // 头部添加
    dq1.push_back(200);
    dq1.push_front(25);
    cout << "添加元素后dq1: ";
    for (int num : dq1) cout << num << " ";
    cout << endl;

    // 访问元素
    cout << "dq3[2] = " << dq3[2] << endl;            // 随机访问
    cout << "dq3.at(2) = " << dq3.at(2) << endl;      // 带边界检查
    cout << "dq3.front() = " << dq3.front() << endl;  // 第一个元素
    cout << "dq3.back() = " << dq3.back() << endl;    // 最后一个元素

    // 3. 插入和删除操作
    cout << "\n3. 插入和删除操作:" << endl;

    // 在指定位置插入
    auto it = dq3.begin();
    advance(it, 2);  // 移动到第3个位置
    dq3.insert(it, 99);
    cout << "在位置2插入99后dq3: ";
    for (int num : dq3) cout << num << " ";
    cout << endl;

    // 插入多个元素
    it = dq3.begin();
    advance(it, 3);
    dq3.insert(it, 3, 88);  // 插入3个88
    cout << "插入3个88后dq3: ";
    for (int num : dq3) cout << num << " ";
    cout << endl;

    // 删除指定位置元素
    it = dq3.begin();
    advance(it, 2);
    dq3.erase(it);
    cout << "删除位置2元素后dq3: ";
    for (int num : dq3) cout << num << " ";
    cout << endl;

    // 删除范围元素
    it = dq3.begin();
    auto it2 = dq3.begin();
    advance(it, 1);
    advance(it2, 4);
    dq3.erase(it, it2);  // 删除[1, 4)位置的元素
    cout << "删除范围元素后dq3: ";
    for (int num : dq3) cout << num << " ";
    cout << endl;

    // 删除头部和尾部元素
    dq3.pop_front();
    dq3.pop_back();
    cout << "pop_front和pop_back后dq3: ";
    for (int num : dq3) cout << num << " ";
    cout << endl;

    // 4. 容量操作
    cout << "\n4. 容量操作:" << endl;

    cout << "dq3大小: " << dq3.size() << endl;
    cout << "dq3是否为空: " << (dq3.empty() ? "是" : "否") << endl;

    // 调整大小
    dq3.resize(8, 0);  // 调整大小为8，新增元素初始化为0
    cout << "调整大小后dq3: ";
    for (int num : dq3) cout << num << " ";
    cout << endl;

    // 清空deque
    deque<int> dq5 = {1, 2, 3, 4, 5};
    dq5.clear();
    cout << "清空后dq5大小: " << dq5.size() << endl;

    // 5. 迭代器使用
    cout << "\n5. 迭代器使用:" << endl;

    cout << "使用迭代器遍历dq4: ";
    for (deque<int>::iterator it = dq4.begin(); it != dq4.end(); ++it)
    {
        cout << *it << " ";
    }
    cout << endl;

    cout << "使用反向迭代器遍历dq4: ";
    for (deque<int>::reverse_iterator rit = dq4.rbegin(); rit != dq4.rend(); ++rit)
    {
        cout << *rit << " ";
    }
    cout << endl;

    // 6. 算法应用
    cout << "\n6. 算法应用:" << endl;

    deque<int> dq6 = {5, 3, 8, 1, 9, 2};

    // 排序
    sort(dq6.begin(), dq6.end());
    cout << "排序后dq6: ";
    for (int num : dq6) cout << num << " ";
    cout << endl;

    // 查找
    auto find_it = find(dq6.begin(), dq6.end(), 8);
    if (find_it != dq6.end())
    {
        cout << "找到元素8，位置: " << distance(dq6.begin(), find_it) << endl;
    }

    // 反转
    reverse(dq6.begin(), dq6.end());
    cout << "反转后dq6: ";
    for (int num : dq6) cout << num << " ";
    cout << endl;

    // 7. 与vector的比较
    cout << "\n7. deque与vector的比较:" << endl;

    // 测试头部插入性能（deque优势）
    cout << "头部插入性能比较:" << endl;
    cout << "deque在头部插入元素效率高，vector在头部插入需要移动所有元素" << endl;

    // 测试随机访问性能（两者都高效）
    cout << "随机访问性能: deque和vector都支持O(1)随机访问" << endl;

    // 8. 实际应用场景
    cout << "\n8. 实际应用场景:" << endl;

    // 场景1：滑动窗口最大值
    cout << "场景1: 滑动窗口最大值问题" << endl;
    deque<int> window;
    vector<int> nums = {1, 3, -1, -3, 5, 3, 6, 7};
    int k = 3;

    cout << "数组: ";
    for (int num : nums) cout << num << " ";
    cout << endl;
    cout << "滑动窗口大小: " << k << endl;

    // 场景2：双端队列实现队列和栈
    cout << "\n场景2: 使用deque实现队列和栈" << endl;

    // 作为队列使用（FIFO）
    deque<int> queue_dq;
    queue_dq.push_back(1);  // 入队
    queue_dq.push_back(2);
    queue_dq.push_back(3);
    cout << "队列操作:" << endl;
    cout << "队首: " << queue_dq.front() << endl;
    queue_dq.pop_front();  // 出队
    cout << "出队后队首: " << queue_dq.front() << endl;

    // 作为栈使用（LIFO）
    deque<int> stack_dq;
    stack_dq.push_back(1);  // 入栈
    stack_dq.push_back(2);
    stack_dq.push_back(3);
    cout << "\n栈操作:" << endl;
    cout << "栈顶: " << stack_dq.back() << endl;
    stack_dq.pop_back();  // 出栈
    cout << "出栈后栈顶: " << stack_dq.back() << endl;

    // 9. 性能提示
    cout << "\n9. 性能提示:" << endl;
    cout << "1. 如果需要频繁在头部和尾部插入/删除元素，deque是最佳选择" << endl;
    cout << "2. deque支持随机访问，但访问速度略慢于vector（由于内存不连续）" << endl;
    cout << "3. deque的内存分配比vector更复杂，但避免了vector的大规模数据搬移" << endl;
    cout << "4. 在中间插入/删除元素时，deque和vector性能相似（都需要移动元素）" << endl;
    cout << "5. deque的迭代器比vector的迭代器更复杂，但功能更强大" << endl;

    cout << "\n========== deque示例结束 ==========" << endl;

    return 0;
}
