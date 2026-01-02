/**
 * @file set.cpp
 * @brief set容器用法示例
 * 
 * set是C++标准模板库(STL)中的关联容器，存储唯一元素
 * 特点：
 * 1. 唯一性：容器中的元素都是唯一的，不允许重复
 * 2. 有序性：元素按照键值自动排序（默认升序）
 * 3. 红黑树：内部使用红黑树实现，保证操作效率
 * 4. 不可修改：元素值不可直接修改，需要先删除再插入
 * 
 * 常用操作时间复杂度：
 * - 插入元素：O(log n)
 * - 删除元素：O(log n)
 * - 查找元素：O(log n)
 * - 遍历元素：O(n)
 */

#include <iostream>
#include <set>
#include <vector>
#include <algorithm>

using namespace std;

int main() {
    cout << "========== set容器用法示例 ==========" << endl;
    
    // 1. 创建和初始化set
    cout << "\n1. 创建和初始化set:" << endl;
    
    // 空set
    set<int> s1;
    cout << "空set大小: " << s1.size() << endl;
    
    // 使用初始化列表
    set<int> s2 = {5, 3, 8, 1, 9, 2};
    cout << "s2: ";
    for (int num : s2) cout << num << " ";
    cout << endl;
    
    // 从数组初始化
    int arr[] = {6, 7, 8, 9, 10, 6, 7};  // 注意有重复元素
    set<int> s3(arr, arr + 7);
    cout << "s3（自动去重）: ";
    for (int num : s3) cout << num << " ";
    cout << endl;
    
    // 从vector初始化
    vector<int> vec = {3, 1, 4, 1, 5, 9, 2, 6};
    set<int> s4(vec.begin(), vec.end());
    cout << "s4（从vector初始化）: ";
    for (int num : s4) cout << num << " ";
    cout << endl;
    
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;
    
    // 插入元素
    s1.insert(10);
    s1.insert(30);
    s1.insert(20);
    s1.insert(40);
    s1.insert(30);  // 重复元素，不会被插入
    
    cout << "插入元素后s1: ";
    for (int num : s1) cout << num << " ";
    cout << endl;
    cout << "s1大小: " << s1.size() << endl;
    
    // 插入多个元素
    s1.insert({50, 60, 70, 20});  // 20已存在，不会被插入
    cout << "批量插入后s1: ";
    for (int num : s1) cout << num << " ";
    cout << endl;
    
    // 3. 查找操作
    cout << "\n3. 查找操作:" << endl;
    
    // 使用find()查找元素
    auto it = s2.find(8);
    if (it != s2.end()) {
        cout << "在s2中找到元素8" << endl;
    } else {
        cout << "在s2中未找到元素8" << endl;
    }
    
    it = s2.find(100);
    if (it == s2.end()) {
        cout << "在s2中未找到元素100" << endl;
    }
    
    // 使用count()检查元素是否存在
    cout << "元素3在s2中出现的次数: " << s2.count(3) << endl;
    cout << "元素100在s2中出现的次数: " << s2.count(100) << endl;
    
    // 使用lower_bound()和upper_bound()
    set<int> s5 = {10, 20, 30, 40, 50, 60, 70, 80, 90};
    
    auto lb = s5.lower_bound(35);  // 第一个 >= 35 的元素
    auto ub = s5.upper_bound(65);  // 第一个 > 65 的元素
    
    cout << "s5中 >=35 的第一个元素: " << (lb != s5.end() ? to_string(*lb) : "无") << endl;
    cout << "s5中 >65 的第一个元素: " << (ub != s5.end() ? to_string(*ub) : "无") << endl;
    
    // 获取范围 [35, 65] 的元素
    cout << "s5中 [35, 65] 范围内的元素: ";
    for (auto it = s5.lower_bound(35); it != s5.upper_bound(65); ++it) {
        cout << *it << " ";
    }
    cout << endl;
    
    // 4. 删除操作
    cout << "\n4. 删除操作:" << endl;
    
    set<int> s6 = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    cout << "原始s6: ";
    for (int num : s6) cout << num << " ";
    cout << endl;
    
    // 删除指定元素
    s6.erase(5);
    cout << "删除元素5后s6: ";
    for (int num : s6) cout << num << " ";
    cout << endl;
    
    // 删除迭代器指向的元素
    it = s6.find(8);
    if (it != s6.end()) {
        s6.erase(it);
    }
    cout << "删除元素8后s6: ";
    for (int num : s6) cout << num << " ";
    cout << endl;
    
    // 删除范围元素
    auto it1 = s6.lower_bound(3);
    auto it2 = s6.upper_bound(7);
    s6.erase(it1, it2);
    cout << "删除[3,7]范围后s6: ";
    for (int num : s6) cout << num << " ";
    cout << endl;
    
    // 5. 集合运算
    cout << "\n5. 集合运算:" << endl;
    
    set<int> A = {1, 2, 3, 4, 5};
    set<int> B = {4, 5, 6, 7, 8};
    
    cout << "集合A: ";
    for (int num : A) cout << num << " ";
    cout << endl;
    
    cout << "集合B: ";
    for (int num : B) cout << num << " ";
    cout << endl;
    
    // 并集
    set<int> union_set;
    set_union(A.begin(), A.end(), B.begin(), B.end(), 
              inserter(union_set, union_set.begin()));
    cout << "A ∪ B (并集): ";
    for (int num : union_set) cout << num << " ";
    cout << endl;
    
    // 交集
    set<int> intersect_set;
    set_intersection(A.begin(), A.end(), B.begin(), B.end(),
                     inserter(intersect_set, intersect_set.begin()));
    cout << "A ∩ B (交集): ";
    for (int num : intersect_set) cout << num << " ";
    cout << endl;
    
    // 差集
    set<int> diff_set;
    set_difference(A.begin(), A.end(), B.begin(), B.end(),
                   inserter(diff_set, diff_set.begin()));
    cout << "A - B (差集): ";
    for (int num : diff_set) cout << num << " ";
    cout << endl;
    
    // 对称差集
    set<int> sym_diff_set;
    set_symmetric_difference(A.begin(), A.end(), B.begin(), B.end(),
                             inserter(sym_diff_set, sym_diff_set.begin()));
    cout << "A Δ B (对称差集): ";
    for (int num : sym_diff_set) cout << num << " ";
    cout << endl;
    
    // 6. 自定义比较函数
    cout << "\n6. 自定义比较函数:" << endl;
    
    // 降序set
    set<int, greater<int>> descending_set = {5, 3, 8, 1, 9, 2};
    cout << "降序set: ";
    for (int num : descending_set) cout << num << " ";
    cout << endl;
    
    // 自定义结构体set
    struct Person {
        string name;
        int age;
        
        bool operator<(const Person& other) const {
            return age < other.age;  // 按年龄排序
        }
    };
    
    set<Person> person_set;
    person_set.insert({"Alice", 25});
    person_set.insert({"Bob", 30});
    person_set.insert({"Charlie", 20});
    person_set.insert({"David", 25});  // 年龄相同，但name不同，可以插入
    
    cout << "按年龄排序的Person set:" << endl;
    for (const auto& p : person_set) {
        cout << p.name << " (" << p.age << "岁)" << endl;
    }
    
    // 7. 实际应用场景
    cout << "\n7. 实际应用场景:" << endl;
    
    // 场景1：去重
    cout << "场景1: 数组去重" << endl;
    vector<int> numbers = {1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 5};
    set<int> unique_numbers(numbers.begin(), numbers.end());
    
    cout << "原始数组: ";
    for (int num : numbers) cout << num << " ";
    cout << endl;
    
    cout << "去重后: ";
    for (int num : unique_numbers) cout << num << " ";
    cout << endl;
    
    // 场景2：黑名单过滤
    cout << "\n场景2: 黑名单过滤" << endl;
    set<string> blacklist = {"spam@example.com", "bad@domain.com", "fake@test.com"};
    vector<string> emails = {"user@example.com", "spam@example.com", 
                            "admin@domain.com", "bad@domain.com", 
                            "test@test.com"};
    
    cout << "邮箱列表: ";
    for (const auto& email : emails) cout << email << " ";
    cout << endl;
    
    cout << "过滤后有效邮箱: ";
    for (const auto& email : emails) {
        if (blacklist.find(email) == blacklist.end()) {
            cout << email << " ";
        }
    }
    cout << endl;
    
    // 场景3：排行榜（按分数排序）
    cout << "\n场景3: 排行榜" << endl;
    
    struct Player {
        string name;
        int score;
        
        bool operator<(const Player& other) const {
            // 按分数降序排序，分数相同按名字升序
            if (score != other.score) {
                return score > other.score;
            }
            return name < other.name;
        }
    };
    
    set<Player> leaderboard;
    leaderboard.insert({"Alice", 100});
    leaderboard.insert({"Bob", 150});
    leaderboard.insert({"Charlie", 100});
    leaderboard.insert({"David", 200});
    leaderboard.insert({"Eve", 150});
    
    cout << "排行榜:" << endl;
    int rank = 1;
    for (const auto& player : leaderboard) {
        cout << rank++ << ". " << player.name << " - " << player.score << "分" << endl;
    }
    
    // 8. 性能提示
    cout << "\n8. 性能提示:" << endl;
    cout << "1. set基于红黑树实现，所有操作都是O(log n)" << endl;
    cout << "2. set中的元素不可直接修改，需要先删除再插入" << endl;
    cout << "3. set自动维护元素有序性，但插入和删除成本较高" << endl;
    cout << "4. 如果需要快速查找且不关心顺序，考虑使用unordered_set" << endl;
    cout << "5. set的迭代器在插入/删除操作后可能失效，需要特别注意" << endl;
    cout << "6. set占用内存较大，每个元素需要额外存储颜色信息和指针" << endl;
    
    // 9. 与vector的比较
    cout << "\n9. set与vector的比较:" << endl;
    cout << "1. set自动去重和排序，vector需要手动处理" << endl;
    cout << "2. set查找效率O(log n)，vector查找效率O(n)" << endl;
    cout << "3. set插入/删除效率O(log n)，vector在中间插入/删除效率O(n)" << endl;
    cout << "4. set内存开销大，vector内存连续、缓存友好" << endl;
    cout << "5. set不支持随机访问，vector支持O(1)随机访问" << endl;
    
    cout << "\n========== set示例结束 ==========" << endl;
    
    return 0;
}
