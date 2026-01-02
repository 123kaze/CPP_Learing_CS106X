/**
 * @file unordered_map.cpp
 * @brief unordered_map容器用法示例
 * 
 * unordered_map是C++标准模板库(STL)中的无序关联容器，存储键值对
 * 特点：
 * 1. 键值对存储：每个元素是一个pair<key, value>
 * 2. 键唯一性：每个键在unordered_map中只能出现一次
 * 3. 无序性：元素不按特定顺序存储，而是根据键的哈希值组织
 * 4. 哈希表：内部使用哈希表实现，提供平均O(1)的查找效率
 * 5. 快速查找：通过哈希函数快速定位键对应的值
 * 
 * 常用操作时间复杂度（平均情况）：
 * - 插入元素：O(1)
 * - 删除元素：O(1)
 * - 查找元素：O(1)
 * - 访问元素：O(1)
 * 最坏情况：O(n)（哈希冲突严重时）
 */

#include <iostream>
#include <unordered_map>
#include <string>
#include <vector>
#include <algorithm>
#include <climits>

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
    cout << "========== unordered_map容器用法示例 ==========" << endl;
    
    // 1. 创建和初始化unordered_map
    cout << "\n1. 创建和初始化unordered_map:" << endl;
    
    // 空unordered_map
    unordered_map<string, int> um1;
    cout << "空unordered_map大小: " << um1.size() << endl;
    cout << "桶数量: " << um1.bucket_count() << endl;
    
    // 使用初始化列表
    unordered_map<string, int> um2 = {
        {"Alice", 25},
        {"Bob", 30},
        {"Charlie", 35},
        {"Alice", 40}  // 重复键，只会保留一个（通常是第一个）
    };
    
    cout << "um2内容:" << endl;
    for (const auto& pair : um2) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    cout << "um2大小: " << um2.size() << endl;
    
    // 从vector初始化
    vector<pair<string, int>> data = {
        {"David", 40},
        {"Eve", 28},
        {"Frank", 32},
        {"David", 50}  // 重复键
    };
    unordered_map<string, int> um3(data.begin(), data.end());
    
    cout << "um3内容:" << endl;
    for (const auto& pair : um3) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;
    
    // 插入元素
    um1["John"] = 28;           // 使用下标操作符插入
    um1.insert({"Mary", 32});   // 使用insert插入
    um1.emplace("Tom", 45);     // 使用emplace插入
    
    // 尝试插入已存在的键
    auto result = um1.insert({"John", 30});  // John已存在，不会插入
    if (!result.second) {
        cout << "插入失败，键'John'已存在，值为: " << um1["John"] << endl;
    }
    
    cout << "um1内容:" << endl;
    for (const auto& pair : um1) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    // 插入多个元素
    um1.insert({{"Kate", 29}, {"Mike", 33}, {"John", 31}});  // John已存在，不会插入
    cout << "批量插入后um1大小: " << um1.size() << endl;
    
    // 3. 访问元素
    cout << "\n3. 访问元素:" << endl;
    
    // 使用下标操作符访问（如果键不存在会创建）
    cout << "um1[\"John\"] = " << um1["John"] << endl;
    cout << "um1[\"Jane\"] = " << um1["Jane"] << endl;  // Jane不存在，会创建并赋默认值0
    
    cout << "访问后um1内容:" << endl;
    for (const auto& pair : um1) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    // 使用at()访问（如果键不存在会抛出异常）
    try {
        cout << "um1.at(\"Mary\") = " << um1.at("Mary") << endl;
        cout << "um1.at(\"Nonexistent\") = " << um1.at("Nonexistent") << endl;
    } catch (const out_of_range& e) {
        cout << "异常: " << e.what() << endl;
    }
    
    // 4. 查找操作
    cout << "\n4. 查找操作:" << endl;
    
    // 使用find()查找元素
    auto it = um2.find("Bob");
    if (it != um2.end()) {
        cout << "找到Bob，年龄: " << it->second << endl;
    } else {
        cout << "未找到Bob" << endl;
    }
    
    it = um2.find("David");
    if (it == um2.end()) {
        cout << "未找到David" << endl;
    }
    
    // 使用count()检查键是否存在
    cout << "键'Alice'在um2中出现的次数: " << um2.count("Alice") << endl;
    cout << "键'David'在um2中出现的次数: " << um2.count("David") << endl;
    
    // 使用contains()检查键是否存在（C++20）
    // cout << "um2是否包含'Charlie': " << um2.contains("Charlie") << endl;
    
    // 5. 删除操作
    cout << "\n5. 删除操作:" << endl;
    
    unordered_map<string, int> um4 = {
        {"A", 1}, {"B", 2}, {"C", 3}, {"D", 4}, {"E", 5},
        {"F", 6}, {"G", 7}, {"H", 8}, {"I", 9}, {"J", 10}
    };
    
    cout << "原始um4大小: " << um4.size() << endl;
    
    // 删除指定键
    um4.erase("C");
    cout << "删除键'C'后um4大小: " << um4.size() << endl;
    
    // 删除迭代器指向的元素
    it = um4.find("F");
    if (it != um4.end()) {
        um4.erase(it);
    }
    cout << "删除键'F'后um4大小: " << um4.size() << endl;
    
    // 删除多个键
    vector<string> keys_to_remove = {"D", "G", "I"};
    for (const auto& key : keys_to_remove) {
        um4.erase(key);
    }
    cout << "删除D,G,I后um4大小: " << um4.size() << endl;
    
    // 清空unordered_map
    um4.clear();
    cout << "清空后um4大小: " << um4.size() << endl;
    
    // 6. 哈希表相关操作
    cout << "\n6. 哈希表相关操作:" << endl;
    
    unordered_map<int, string> um5 = {
        {10, "A"}, {20, "B"}, {30, "C"}, {40, "D"}, {50, "E"},
        {60, "F"}, {70, "G"}, {80, "H"}, {90, "I"}
    };
    
    cout << "um5大小: " << um5.size() << endl;
    cout << "桶数量: " << um5.bucket_count() << endl;
    cout << "负载因子: " << um5.load_factor() << endl;
    cout << "最大负载因子: " << um5.max_load_factor() << endl;
    
    // 查找特定键所在的桶
    int key_to_find = 30;
    size_t bucket = um5.bucket(key_to_find);
    cout << "键" << key_to_find << "在桶" << bucket << "中" << endl;
    
    // 遍历桶
    cout << "桶分布情况:" << endl;
    for (size_t i = 0; i < um5.bucket_count(); i++) {
        size_t bucket_size = um5.bucket_size(i);
        if (bucket_size > 0) {
            cout << "  桶" << i << ": " << bucket_size << "个元素 (";
            for (auto local_it = um5.begin(i); local_it != um5.end(i); ++local_it) {
                cout << local_it->first << ":" << local_it->second << " ";
            }
            cout << ")" << endl;
        }
    }
    
    // 调整桶数量
    um5.rehash(50);
    cout << "rehash(50)后桶数量: " << um5.bucket_count() << endl;
    
    // 预留空间
    unordered_map<int, string> um6;
    um6.reserve(100);
    cout << "reserve(100)后um6桶数量: " << um6.bucket_count() << endl;
    
    // 7. 遍历unordered_map
    cout << "\n7. 遍历unordered_map:" << endl;
    
    cout << "使用范围for循环遍历um2:" << endl;
    for (const auto& pair : um2) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    cout << "使用迭代器遍历um2:" << endl;
    for (auto it = um2.begin(); it != um2.end(); ++it) {
        cout << "  " << it->first << ": " << it->second << endl;
    }
    
    // 注意：unordered_map没有反向迭代器
    // cout << "使用反向迭代器遍历um2:" << endl;  // 错误！unordered_map没有rbegin()/rend()
    
    // 使用结构化绑定（C++17）
    cout << "使用结构化绑定遍历um2:" << endl;
    for (const auto& [key, value] : um2) {
        cout << "  " << key << ": " << value << endl;
    }
    
    // 8. 自定义类型unordered_map
    cout << "\n8. 自定义类型unordered_map:" << endl;
    
    unordered_map<Person, string, PersonHash> person_map;
    
    person_map[{"Alice", 25}] = "工程师";
    person_map[{"Bob", 30}] = "医生";
    person_map[{"Charlie", 35}] = "教师";
    person_map[{"Alice", 25}] = "高级工程师";  // 更新值
    
    cout << "Person unordered_map:" << endl;
    for (const auto& [person, job] : person_map) {
        cout << "  " << person.name << " (" << person.age << "岁): " << job << endl;
    }
    
    // 9. 实际应用场景
    cout << "\n9. 实际应用场景:" << endl;
    
    // 场景1：单词频率统计
    cout << "场景1: 单词频率统计" << endl;
    string text = "apple banana apple cherry banana apple date";
    unordered_map<string, int> word_freq;
    
    // 简单分词
    string word;
    for (char ch : text) {
        if (ch == ' ') {
            if (!word.empty()) {
                word_freq[word]++;
                word.clear();
            }
        } else {
            word += ch;
        }
    }
    if (!word.empty()) {
        word_freq[word]++;
    }
    
    cout << "文本: " << text << endl;
    cout << "单词频率:" << endl;
    for (const auto& [w, freq] : word_freq) {
        cout << "  " << w << ": " << freq << endl;
    }
    
    // 场景2：缓存实现
    cout << "\n场景2: 缓存实现" << endl;
    
    // 简单的LRU缓存模拟
    unordered_map<int, pair<string, int>> cache;  // key -> {value, timestamp}
    const int CACHE_SIZE = 3;
    int current_time = 0;
    
    auto access_cache = [&](int key, const string& value) {
        cout << "访问键" << key << " (" << value << ")" << endl;
        
        if (cache.find(key) != cache.end()) {
            // 缓存命中，更新时间戳
            cache[key].second = current_time;
            cout << "  缓存命中" << endl;
        } else {
            // 缓存未命中
            if (cache.size() >= CACHE_SIZE) {
                // 找到最久未使用的键
                int lru_key = -1;
                int oldest_time = INT_MAX;
                for (const auto& [k, v] : cache) {
                    if (v.second < oldest_time) {
                        oldest_time = v.second;
                        lru_key = k;
                    }
                }
                // 移除最久未使用的
                cout << "  缓存已满，移除键" << lru_key << endl;
                cache.erase(lru_key);
            }
            // 添加新条目
            cache[key] = {value, current_time};
        }
        
        current_time++;
        
        // 显示当前缓存状态
        cout << "  当前缓存: ";
        for (const auto& [k, v] : cache) {
            cout << k << ":" << v.first << " ";
        }
        cout << endl;
    };
    
    access_cache(1, "Data1");
    access_cache(2, "Data2");
    access_cache(3, "Data3");
    access_cache(1, "Data1");  // 再次访问，应该命中
    access_cache(4, "Data4");  // 应该移除最久未使用的(2)
    
    // 场景3：分组统计
    cout << "\n场景3: 分组统计" << endl;
    
    struct Student {
        string name;
        string department;
        int score;
    };
    
    vector<Student> students = {
        {"Alice", "CS", 85},
        {"Bob", "Math", 92},
        {"Charlie", "CS", 78},
        {"David", "Physics", 88},
        {"Eve", "Math", 95},
        {"Frank", "CS", 82}
    };
    
    unordered_map<string, vector<Student>> dept_students;
    unordered_map<string, double> dept_avg_score;
    
    for (const auto& student : students) {
        dept_students[student.department].push_back(student);
    }
    
    cout << "按院系分组的学生:" << endl;
    for (const auto& [dept, stu_list] : dept_students) {
        double total_score = 0;
        cout << "  院系" << dept << ": ";
        for (const auto& student : stu_list) {
            cout << student.name << "(" << student.score << ") ";
            total_score += student.score;
        }
        double avg_score = total_score / stu_list.size();
        cout << "平均分: " << avg_score << endl;
        dept_avg_score[dept] = avg_score;
    }
    
    // 10. 性能比较和优化提示
    cout << "\n10. 性能比较和优化提示:" << endl;
    
    cout << "unordered_map vs map 比较:" << endl;
    cout << "1. 查找性能: unordered_map平均O(1)，map O(log n)" << endl;
    cout << "2. 内存使用: unordered_map需要哈希表开销，map需要红黑树节点开销" << endl;
    cout << "3. 元素顺序: unordered_map无序，map有序" << endl;
    cout << "4. 迭代器稳定性: unordered_map迭代器可能失效，map迭代器稳定" << endl;
    
    cout << "\n性能优化提示:" << endl;
    cout << "1. 使用reserve()预留空间减少rehash操作" << endl;
    cout << "2. 提供良好的哈希函数减少冲突" << endl;
    cout << "3. 调整max_load_factor()平衡空间和时间效率" << endl;
    cout << "4. 自定义类型必须提供哈希函数和相等比较运算符" << endl;
    cout << "5. 使用emplace()代替insert()提高插入效率" << endl;
    cout << "6. 避免频繁的[]操作符访问不存在的键（会创建新条目）" << endl;
    
    cout << "\n选择建议:" << endl;
    cout << "1. 需要快速查找且不关心顺序：unordered_map" << endl;
    cout << "2. 需要有序遍历或范围查询：map" << endl;
    cout << "3. 键类型没有好的哈希函数：map" << endl;
    cout << "4. 需要稳定的迭代器：map" << endl;
    cout << "5. 内存非常紧张：测试两种容器的实际内存使用" << endl;
    
    cout << "\n========== unordered_map示例结束 ==========" << endl;
    
    return 0;
}
