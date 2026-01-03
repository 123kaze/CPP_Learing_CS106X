/**
 * @file unordered_set.cpp
 * @brief unordered_set容器用法示例
 * 
 * unordered_set是C++标准模板库(STL)中的无序关联容器，存储唯一元素
 * 特点：
 * 1. 唯一性：容器中的元素都是唯一的，不允许重复
 * 2. 无序性：元素不按特定顺序存储，而是根据哈希值组织
 * 3. 哈希表：内部使用哈希表实现，提供平均O(1)的查找效率
 * 4. 快速查找：通过哈希函数快速定位元素
 * 
 * 常用操作时间复杂度（平均情况）：
 * - 插入元素：O(1)
 * - 删除元素：O(1)
 * - 查找元素：O(1)
 * - 访问元素：O(1)
 * 最坏情况：O(n)（哈希冲突严重时）
 */

#include <iostream>
#include <unordered_set>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// 自定义类型需要提供哈希函数
struct Person {
    string name;
    int age;
    
    bool operator==(const Person& other) const {
        return name == other.name && age == other.age;
    }
};

// 自定义哈希函数
struct PersonHash {
    size_t operator()(const Person& p) const {
        return hash<string>()(p.name) ^ (hash<int>()(p.age) << 1);
    }
};

int main() {
    cout << "========== unordered_set容器用法示例 ==========" << endl;
    
    // 1. 创建和初始化unordered_set
    cout << "\n1. 创建和初始化unordered_set:" << endl;
    
    // 空unordered_set
    unordered_set<int> us1;
    cout << "空unordered_set大小: " << us1.size() << endl;
    cout << "桶数量: " << us1.bucket_count() << endl;
    
    // 使用初始化列表
    unordered_set<int> us2 = {5, 3, 8, 1, 9, 2, 5, 3};  // 重复元素会自动去重
    cout << "us2: ";
    for (int num : us2) cout << num << " ";
    cout << endl;
    cout << "us2大小: " << us2.size() << endl;
    
    // 从vector初始化
    vector<int> vec = {3, 1, 4, 1, 5, 9, 2, 6, 3};
    unordered_set<int> us3(vec.begin(), vec.end());
    cout << "us3（从vector初始化，自动去重）: ";
    for (int num : us3) cout << num << " ";
    cout << endl;
    
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;
    
    // 插入元素
    us1.insert(10);
    us1.insert(30);
    us1.insert(20);
    us1.insert(40);
    us1.insert(30);  // 重复元素，不会被插入
    
    cout << "插入元素后us1: ";
    for (int num : us1) cout << num << " ";
    cout << endl;
    cout << "us1大小: " << us1.size() << endl;
    
    // 插入多个元素
    us1.insert({50, 60, 70, 20});  // 20已存在，不会被插入
    cout << "批量插入后us1: ";
    
    cout << endl;
    
    // 使用emplace插入  
    us1.emplace(80);
    us1.emplace(90);
    for (int num : us1) cout << num << " "<<endl;
    cout << "emplace插入后us1大小: " << us1.size() << endl;
    
    // 3. 查找操作
    cout << "\n3. 查找操作:" << endl;
    
    // 使用find()查找元素
    auto it = us2.find(8);
    if (it != us2.end()) {
        cout << "在us2中找到元素8" << endl;
    } else {
        cout << "在us2中未找到元素8" << endl;
    }
    
    it = us2.find(100);
    if (it == us2.end()) {
        cout << "在us2中未找到元素100" << endl;
    }
    
    // 使用count()检查元素是否存在
    cout << "元素3在us2中出现的次数: " << us2.count(3) << endl;
    cout << "元素100在us2中出现的次数: " << us2.count(100) << endl;
    
    // 使用contains()检查元素是否存在（C++20）
    cout << "us2是否包含5: " << us2.contains(5) << endl;
    
    // 4. 删除操作
    cout << "\n4. 删除操作:" << endl;
    
    unordered_set<int> us4 = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    cout << "原始us4: ";
    for (int num : us4) cout << num << " ";
    cout << endl;
    
    // 删除指定元素
    us4.erase(5);
    cout << "删除元素5后us4: ";
    for (int num : us4) cout << num << " ";
    cout << endl;
    
    // 删除迭代器指向的元素
    it = us4.find(8);
    if (it != us4.end()) {
        us4.erase(it);
    }
    cout << "删除元素8后us4: ";
    for (int num : us4) cout << num << " ";
    cout << endl;
    
    // 删除范围元素（unordered_set不支持范围删除，但可以连续删除）
    vector<int> to_remove = {3, 7, 9};
    for (int num : to_remove) {
        us4.erase(num);
    }
    cout << "删除3,7,9后us4: ";
    for (int num : us4) cout << num << " ";
    cout << endl;
    
    // 清空unordered_set
    us4.clear();
    cout << "清空后us4大小: " << us4.size() << endl;
    
    // 5. 哈希表相关操作
    cout << "\n5. 哈希表相关操作:" << endl;
    
    unordered_set<int> us5 = {10, 20, 30, 40, 50, 60, 70, 80, 90};
    
    cout << "us5大小: " << us5.size() << endl;
    cout << "桶数量: " << us5.bucket_count() << endl;
    cout << "负载因子: " << us5.load_factor() << endl;
    cout << "最大负载因子: " << us5.max_load_factor() << endl;
    
    // 遍历桶
    cout << "桶分布情况:" << endl;
    for (size_t i = 0; i < us5.bucket_count(); i++) {
        cout << "  桶" << i << ": " << us5.bucket_size(i) << "个元素";
        if (us5.bucket_size(i) > 0) {
            cout << " (";
            for (auto local_it = us5.begin(i); local_it != us5.end(i); ++local_it) {
                cout << *local_it << " ";
            }
            cout << ")";
        }
        cout << endl;
    }
    
    // 调整桶数量
    us5.rehash(50);
    cout << "rehash(50)后桶数量: " << us5.bucket_count() << endl;
    
    // 预留空间
    unordered_set<int> us6;
    us6.reserve(100);
    cout << "reserve(100)后us6桶数量: " << us6.bucket_count() << endl;
    
    // 6. 遍历unordered_set
    cout << "\n6. 遍历unordered_set:" << endl;
    
    cout << "使用范围for循环遍历us2:" << endl;
    cout << "  ";
    for (int num : us2) {
        cout << num << " ";
    }
    cout << endl;
    
    cout << "使用迭代器遍历us2:" << endl;
    cout << "  ";
    for (auto it = us2.begin(); it != us2.end(); ++it) {
        cout << *it << " ";
    }
    cout << endl;
    
    // 注意：unordered_set没有反向迭代器
    // cout << "使用反向迭代器遍历us2:" << endl;  // 错误！unordered_set没有rbegin()/rend()
    
    // 7. 自定义类型unordered_set
    cout << "\n7. 自定义类型unordered_set:" << endl;
    
    unordered_set<Person, PersonHash> person_set;
    
    person_set.insert({"Alice", 25});
    person_set.insert({"Bob", 30});
    person_set.insert({"Charlie", 35});
    person_set.insert({"Alice", 25});  // 重复，不会被插入
    person_set.insert({"Alice", 30});  // 不同年龄，可以插入
    
    cout << "Person unordered_set:" << endl;
    for (const auto& p : person_set) {
        cout << "  " << p.name << " (" << p.age << "岁)" << endl;
    }
    cout << "大小: " << person_set.size() << endl;
    
    // 8. 实际应用场景
    cout << "\n8. 实际应用场景:" << endl;
    
    // 场景1：快速去重
    cout << "场景1: 快速去重" << endl;
    vector<int> numbers = {1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 5};
    unordered_set<int> unique_numbers(numbers.begin(), numbers.end());
    
    cout << "原始数组: ";
    for (int num : numbers) cout << num << " ";
    cout << endl;
    
    cout << "去重后: ";
    for (int num : unique_numbers) cout << num << " ";
    cout << endl;
    
    // 场景2：查找两数之和
    cout << "\n场景2: 查找两数之和" << endl;
    vector<int> nums = {2, 7, 11, 15, 3, 6};
    int target = 9;
    
    unordered_set<int> num_set;
    cout << "数组: ";
    for (int num : nums) cout << num << " ";
    cout << endl;
    cout << "目标值: " << target << endl;
    
    cout << "两数之和为" << target << "的数对: ";
    for (int num : nums) {
        int complement = target - num;
        if (num_set.find(complement) != num_set.end()) {
            cout << "(" << complement << ", " << num << ") ";
        }
        num_set.insert(num);
    }
    cout << endl;
    
    // 场景3：检测循环引用
    cout << "\n场景3: 检测循环引用（模拟）" << endl;
    
    // 模拟有向图检测环
    unordered_set<int> visited;
    unordered_set<int> recursion_stack;
    
    // 简化版DFS检测环
    auto has_cycle = [&](int node, auto& graph, auto& dfs) -> bool {
        if (recursion_stack.find(node) != recursion_stack.end()) {
            return true;  // 发现环
        }
        if (visited.find(node) != visited.end()) {
            return false;  // 已访问过，无环
        }
        
        visited.insert(node);
        recursion_stack.insert(node);
        
        // 模拟遍历邻居
        // 这里简化处理，实际应用中需要根据具体图结构处理
        
        recursion_stack.erase(node);
        return false;
    };
    
    cout << "循环引用检测算法示例（简化版）" << endl;
    
    // 9. 性能比较：unordered_set vs set
    cout << "\n9. 性能比较：unordered_set vs set:" << endl;
    
    cout << "1. 查找性能:" << endl;
    cout << "   unordered_set: 平均O(1)，最坏O(n)" << endl;
    cout << "   set: O(log n)" << endl;
    
    cout << "2. 内存使用:" << endl;
    cout << "   unordered_set: 需要额外哈希表开销" << endl;
    cout << "   set: 需要红黑树节点开销" << endl;
    
    cout << "3. 元素顺序:" << endl;
    cout << "   unordered_set: 无序" << endl;
    cout << "   set: 有序" << endl;
    
    cout << "4. 选择建议:" << endl;
    cout << "   - 需要快速查找且不关心顺序：unordered_set" << endl;
    cout << "   - 需要有序遍历或范围查询：set" << endl;
    cout << "   - 内存紧张：测试两种容器的实际内存使用" << endl;
    
    // 10. 性能优化提示
    cout << "\n10. 性能优化提示:" << endl;
    cout << "1. 选择合适的哈希函数可以减少冲突，提高性能" << endl;
    cout << "2. 使用reserve()预留空间可以减少rehash操作" << endl;
    cout << "3. 调整max_load_factor()可以平衡空间和时间效率" << endl;
    cout << "4. 自定义类型必须提供哈希函数和相等比较运算符" << endl;
    cout << "5. 频繁插入删除时，unordered_set性能通常优于set" << endl;
    cout << "6. 如果需要有序遍历，不要使用unordered_set" << endl;
    
    cout << "\n========== unordered_set示例结束 ==========" << endl;
    
    return 0;
}
