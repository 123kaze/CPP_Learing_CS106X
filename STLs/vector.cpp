/**
 * @file vector.cpp
 * @brief vector容器用法示例
 * 
 * vector是C++标准模板库(STL)中的动态数组容器
 * 特点：
 * 1. 动态扩容：自动管理内存，可动态调整大小
 * 2. 随机访问：支持O(1)时间的随机访问
 * 3. 连续存储：元素在内存中连续存储，缓存友好
 * 4. 尾部操作高效：在尾部插入/删除元素为O(1)时间复杂度
 * 
 * 常用操作时间复杂度：
 * - 访问元素：O(1)
 * - 尾部插入/删除：O(1)（平摊）
 * - 中间插入/删除：O(n)
 * - 查找：O(n)
 */

#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    cout << "========== vector容器用法示例 ==========" << endl;
    
    // 1. 创建和初始化vector
    cout << "\n1. 创建和初始化vector:" << endl;
    
    // 空vector
    vector<int> vec1;
    cout << "空vector大小: " << vec1.size() << endl;
    
    // 指定大小和初始值
    vector<int> vec2(5, 10);  // 5个元素，每个都是10
    cout << "vec2: ";
    for (int num : vec2) cout << num << " ";
    cout << endl;
    
    // 使用初始化列表
    vector<int> vec3 = {1, 2, 3, 4, 5};
    cout << "vec3: ";
    for (int num : vec3) cout << num << " ";
    cout << endl;
    
    // 从数组初始化
    int arr[] = {6, 7, 8, 9, 10};
    vector<int> vec4(arr, arr + 5);
    cout << "vec4: ";
    for (int num : vec4) cout << num << " ";
    cout << endl;
    
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;
    
    // 添加元素
    vec1.push_back(100);
    vec1.push_back(200);
    vec1.push_back(300);
    cout << "添加元素后vec1: ";
    for (int num : vec1) cout << num << " ";
    cout << endl;
    
    // 访问元素
    cout << "vec3[2] = " << vec3[2] << endl;           // 随机访问
    cout << "vec3.at(2) = " << vec3.at(2) << endl;     // 带边界检查
    cout << "vec3.front() = " << vec3.front() << endl; // 第一个元素
    cout << "vec3.back() = " << vec3.back() << endl;   // 最后一个元素
    
    // 3. 容量相关操作
    cout << "\n3. 容量相关操作:" << endl;
    cout << "vec3大小: " << vec3.size() << endl;
    cout << "vec3容量: " << vec3.capacity() << endl;
    cout << "vec3是否为空: " << (vec3.empty() ? "是" : "否") << endl;
    
    // 调整大小
    vec3.resize(8, 0);  // 调整大小为8，新增元素初始化为0
    cout << "调整大小后vec3: ";
    for (int num : vec3) cout << num << " ";
    cout << endl;
    
    // 预留容量
    vector<int> vec5;
    vec5.reserve(100);  // 预留100个元素的空间
    cout << "预留容量后vec5容量: " << vec5.capacity() << endl;
    
    // 4. 修改操作
    cout << "\n4. 修改操作:" << endl;
    
    // 插入元素
    vec3.insert(vec3.begin() + 2, 99);  // 在位置2插入99
    cout << "插入后vec3: ";
    for (int num : vec3) cout << num << " ";
    cout << endl;
    
    // 删除元素
    vec3.erase(vec3.begin() + 2);  // 删除位置2的元素
    cout << "删除后vec3: ";
    for (int num : vec3) cout << num << " ";
    cout << endl;
    
    // 删除尾部元素
    vec3.pop_back();
    cout << "pop_back后vec3: ";
    for (int num : vec3) cout << num << " ";
    cout << endl;
    
    // 清空vector
    vector<int> vec6 = {1, 2, 3, 4, 5};
    vec6.clear();
    cout << "清空后vec6大小: " << vec6.size() << endl;
    
    // 5. 迭代器使用
    cout << "\n5. 迭代器使用:" << endl;
    
    cout << "使用迭代器遍历vec4: ";
    for (vector<int>::iterator it = vec4.begin(); it != vec4.end(); ++it) {
        cout << *it << " ";
    }
    cout << endl;
    
    cout << "使用反向迭代器遍历vec4: ";
    for (vector<int>::reverse_iterator rit = vec4.rbegin(); rit != vec4.rend(); ++rit) {
        cout << *rit << " ";
    }
    cout << endl;
    
    // 6. 算法应用
    cout << "\n6. 算法应用:" << endl;
    
    // 排序
    vector<int> vec7 = {5, 3, 8, 1, 9, 2};
    sort(vec7.begin(), vec7.end());
    cout << "排序后vec7: ";
    for (int num : vec7) cout << num << " ";
    cout << endl;
    
    // 查找
    auto it = find(vec7.begin(), vec7.end(), 8);
    if (it != vec7.end()) {
        cout << "找到元素8，位置: " << distance(vec7.begin(), it) << endl;
    }
    
    // 反转
    reverse(vec7.begin(), vec7.end());
    cout << "反转后vec7: ";
    for (int num : vec7) cout << num << " ";
    cout << endl;
    
    // 7. 二维vector
    cout << "\n7. 二维vector:" << endl;
    
    vector<vector<int>> matrix = {
        {1, 2, 3},
        {4, 5, 6},
        {7, 8, 9}
    };
    
    cout << "二维vector矩阵:" << endl;
    for (const auto& row : matrix) {
        for (int num : row) {
            cout << num << " ";
        }
        cout << endl;
    }
    
    // 8. 性能提示
    cout << "\n8. 性能提示:" << endl;
    cout << "1. 如果需要频繁在尾部添加元素，vector是最佳选择" << endl;
    cout << "2. 如果需要频繁在中间插入/删除，考虑使用list或deque" << endl;
    cout << "3. 如果知道元素数量，使用reserve()预留空间可避免多次重新分配" << endl;
    cout << "4. vector的迭代器在插入/删除操作后可能失效，需要特别注意" << endl;
    
    cout << "\n========== vector示例结束 ==========" << endl;
    
    return 0;
}
