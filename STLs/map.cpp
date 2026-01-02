/**
 * @file map.cpp
 * @brief map容器用法示例
 * 
 * map是C++标准模板库(STL)中的关联容器，存储键值对
 * 特点：
 * 1. 键值对存储：每个元素是一个pair<key, value>
 * 2. 键唯一性：每个键在map中只能出现一次
 * 3. 有序性：元素按照键自动排序（默认升序）
 * 4. 红黑树：内部使用红黑树实现，保证操作效率
 * 5. 快速查找：通过键可以快速查找对应的值
 * 
 * 常用操作时间复杂度：
 * - 插入元素：O(log n)
 * - 删除元素：O(log n)
 * - 查找元素：O(log n)
 * - 访问元素：O(log n)
 */

#include <iostream>
#include <map>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    cout << "========== map容器用法示例 ==========" << endl;
    
    // 1. 创建和初始化map
    cout << "\n1. 创建和初始化map:" << endl;
    
    // 空map
    map<string, int> m1;
    cout << "空map大小: " << m1.size() << endl;
    
    // 使用初始化列表
    map<string, int> m2 = {
        {"Alice", 25},
        {"Bob", 30},
        {"Charlie", 35}
    };
    
    cout << "m2内容:" << endl;
    for (const auto& pair : m2) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    // 从vector初始化
    vector<pair<string, int>> data = {
        {"David", 40},
        {"Eve", 28},
        {"Frank", 32}
    };
    map<string, int> m3(data.begin(), data.end());
    
    cout << "m3内容:" << endl;
    for (const auto& pair : m3) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;
    
    // 插入元素
    m1["John"] = 28;           // 使用下标操作符插入
    m1.insert({"Mary", 32});   // 使用insert插入
    m1.emplace("Tom", 45);     // 使用emplace插入
    
    // 尝试插入已存在的键
    auto result = m1.insert({"John", 30});  // John已存在，不会插入
    if (!result.second) {
        cout << "插入失败，键'John'已存在，值为: " << m1["John"] << endl;
    }
    
    cout << "m1内容:" << endl;
    for (const auto& pair : m1) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    // 3. 访问元素
    cout << "\n3. 访问元素:" << endl;
    
    // 使用下标操作符访问（如果键不存在会创建）
    cout << "m1[\"John\"] = " << m1["John"] << endl;
    cout << "m1[\"Jane\"] = " << m1["Jane"] << endl;  // Jane不存在，会创建并赋默认值0
    
    cout << "访问后m1内容:" << endl;
    for (const auto& pair : m1) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    // 使用at()访问（如果键不存在会抛出异常）
    try {
        cout << "m1.at(\"Mary\") = " << m1.at("Mary") << endl;
        cout << "m1.at(\"Nonexistent\") = " << m1.at("Nonexistent") << endl;
    } catch (const out_of_range& e) {
        cout << "异常: " << e.what() << endl;
    }
    
    // 4. 查找操作
    cout << "\n4. 查找操作:" << endl;
    
    // 使用find()查找元素
    auto it = m2.find("Bob");
    if (it != m2.end()) {
        cout << "找到Bob，年龄: " << it->second << endl;
    } else {
        cout << "未找到Bob" << endl;
    }
    
    it = m2.find("David");
    if (it == m2.end()) {
        cout << "未找到David" << endl;
    }
    
    // 使用count()检查键是否存在
    cout << "键'Alice'在m2中出现的次数: " << m2.count("Alice") << endl;
    cout << "键'David'在m2中出现的次数: " << m2.count("David") << endl;
    
    // 使用contains()检查键是否存在（C++20）
    // cout << "m2是否包含'Charlie': " << m2.contains("Charlie") << endl;
    
    // 5. 删除操作
    cout << "\n5. 删除操作:" << endl;
    
    map<string, int> m4 = {
        {"A", 1}, {"B", 2}, {"C", 3}, {"D", 4}, {"E", 5},
        {"F", 6}, {"G", 7}, {"H", 8}, {"I", 9}, {"J", 10}
    };
    
    cout << "原始m4:" << endl;
    for (const auto& pair : m4) {
        cout << "  " << pair.first << ": " << pair.second;
    }
    cout << endl;
    
    // 删除指定键
    m4.erase("C");
    cout << "删除键'C'后m4大小: " << m4.size() << endl;
    
    // 删除迭代器指向的元素
    it = m4.find("F");
    if (it != m4.end()) {
        m4.erase(it);
    }
    cout << "删除键'F'后m4大小: " << m4.size() << endl;
    
    // 删除范围元素
    auto it1 = m4.lower_bound("D");
    auto it2 = m4.upper_bound("H");
    m4.erase(it1, it2);
    cout << "删除[D, H)范围后m4大小: " << m4.size() << endl;
    
    cout << "删除后m4:" << endl;
    for (const auto& pair : m4) {
        cout << "  " << pair.first << ": " << pair.second;
    }
    cout << endl;
    
    // 6. 遍历map
    cout << "\n6. 遍历map:" << endl;
    
    cout << "使用范围for循环遍历m2:" << endl;
    for (const auto& pair : m2) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    cout << "使用迭代器遍历m2:" << endl;
    for (auto it = m2.begin(); it != m2.end(); ++it) {
        cout << "  " << it->first << ": " << it->second << endl;
    }
    
    cout << "使用反向迭代器遍历m2:" << endl;
    for (auto rit = m2.rbegin(); rit != m2.rend(); ++rit) {
        cout << "  " << rit->first << ": " << rit->second << endl;
    }
    
    // 7. 自定义比较函数
    cout << "\n7. 自定义比较函数:" << endl;
    
    // 降序map
    map<string, int, greater<string>> descending_map = {
        {"Apple", 10},
        {"Banana", 20},
        {"Cherry", 30}
    };
    
    cout << "降序map:" << endl;
    for (const auto& pair : descending_map) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    // 自定义键类型
    struct Point {
        int x, y;
        
        bool operator<(const Point& other) const {
            if (x != other.x) return x < other.x;
            return y < other.y;
        }
    };
    
    map<Point, string> point_map;
    point_map[{1, 2}] = "A";
    point_map[{3, 4}] = "B";
    point_map[{1, 3}] = "C";
    point_map[{2, 2}] = "D";
    
    cout << "Point map:" << endl;
    for (const auto& pair : point_map) {
        cout << "  (" << pair.first.x << "," << pair.first.y << "): " 
             << pair.second << endl;
    }
    
    // 8. 实际应用场景
    cout << "\n8. 实际应用场景:" << endl;
    
    // 场景1：单词计数
    cout << "场景1: 单词计数" << endl;
    string text = "apple banana apple cherry banana apple date";
    map<string, int> word_count;
    
    // 简单分词（实际应用中需要更复杂的分词逻辑）
    string word;
    for (char ch : text) {
        if (ch == ' ') {
            if (!word.empty()) {
                word_count[word]++;
                word.clear();
            }
        } else {
            word += ch;
        }
    }
    if (!word.empty()) {
        word_count[word]++;
    }
    
    cout << "文本: " << text << endl;
    cout << "单词统计:" << endl;
    for (const auto& pair : word_count) {
        cout << "  " << pair.first << ": " << pair.second << endl;
    }
    
    // 场景2：学生成绩管理
    cout << "\n场景2: 学生成绩管理" << endl;
    
    struct Student {
        string name;
        int score;
    };
    
    map<int, vector<Student>> score_map;  // 按分数分组
    
    vector<Student> students = {
        {"Alice", 85}, {"Bob", 92}, {"Charlie", 85},
        {"David", 78}, {"Eve", 92}, {"Frank", 78}
    };
    
    for (const auto& student : students) {
        score_map[student.score].push_back(student);
    }
    
    cout << "按分数分组的学生:" << endl;
    for (const auto& pair : score_map) {
        cout << "  分数" << pair.first << ": ";
        for (const auto& student : pair.second) {
            cout << student.name << " ";
        }
        cout << endl;
    }
    
    // 场景3：缓存实现（LRU缓存模拟）
    cout << "\n场景3: 缓存实现（LRU缓存模拟）" << endl;
    
    // 简单的缓存实现
    map<int, string> cache;
    const int CACHE_SIZE = 3;
    vector<int> access_order;  // 简化版，实际LRU需要更复杂的数据结构
    
    // 模拟缓存访问
    auto access_cache = [&](int key, const string& value) {
        cout << "访问键" << key << " (" << value << ")" << endl;
        
        if (cache.find(key) != cache.end()) {
            // 缓存命中，更新访问顺序
            auto it = find(access_order.begin(), access_order.end(), key);
            if (it != access_order.end()) {
                access_order.erase(it);
            }
            access_order.insert(access_order.begin(), key);
        } else {
            // 缓存未命中
            if (cache.size() >= CACHE_SIZE) {
                // 移除最久未使用的
                int lru_key = access_order.back();
                cout << "  缓存已满，移除键" << lru_key << endl;
                cache.erase(lru_key);
                access_order.pop_back();
            }
            // 添加新条目
            cache[key] = value;
            access_order.insert(access_order.begin(), key);
        }
        
        // 显示当前缓存状态
        cout << "  当前缓存: ";
        for (const auto& pair : cache) {
            cout << pair.first << ":" << pair.second << " ";
        }
        cout << endl;
    };
    
    access_cache(1, "Data1");
    access_cache(2, "Data2");
    access_cache(3, "Data3");
    access_cache(1, "Data1");  // 再次访问，应该命中
    access_cache(4, "Data4");  // 应该移除最久未使用的(2)
    
    // 9. 性能提示
    cout << "\n9. 性能提示:" << endl;
    cout << "1. map基于红黑树实现，所有操作都是O(log n)" << endl;
    cout << "2. 使用下标操作符[]访问不存在的键会创建新条目" << endl;
    cout << "3. 使用at()访问不存在的键会抛出异常" << endl;
    cout << "4. 插入元素时，使用emplace()比insert()更高效" << endl;
    cout << "5. 如果需要快速查找且不关心顺序，考虑使用unordered_map" << endl;
    cout << "6. map占用内存较大，每个节点需要额外存储颜色信息和指针" << endl;
    cout << "7. 频繁插入删除时，map的性能优于vector但不如unordered_map" << endl;
    
    // 10. 与unordered_map的比较
    cout << "\n10. map与unordered_map的比较:" << endl;
    cout << "1. map有序，unordered_map无序" << endl;
    cout << "2. map基于红黑树，unordered_map基于哈希表" << endl;
    cout << "3. map操作O(log n)，unordered_map平均O(1)，最坏O(n)" << endl;
    cout << "4. map需要定义<运算符，unordered_map需要定义哈希函数" << endl;
    cout << "5. map内存开销较大，unordered_map内存开销较小" << endl;
    cout << "6. map迭代器稳定，unordered_map迭代器可能失效" << endl;
    
    cout << "\n========== map示例结束 ==========" << endl;
    
    return 0;
}
