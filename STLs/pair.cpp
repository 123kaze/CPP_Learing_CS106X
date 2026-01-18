/**
 * @file pair.cpp
 * @brief pair容器用法示例
 *
 * pair是C++标准模板库(STL)中的对组容器，存储两个元素
 * 特点：
 * 1. 两个元素：存储两个值，可以是不同类型
 * 2. 值语义：pair是值类型，可以复制和赋值
 * 3. 成员访问：通过first和second成员访问元素
 * 4. 常用场景：map的键值对、函数返回两个值等
 *
 * 常用操作：
 * - 创建pair：make_pair, pair构造函数
 * - 访问元素：first, second成员
 * - 比较操作：==, !=, <, >, <=, >=
 * - 其他操作：swap, tie, structured binding
 */

#include <algorithm>
#include <cmath>
#include <iostream>
#include <map>
#include <string>
#include <utility>
#include <vector>

using namespace std;

int main()
{
    cout << "========== pair容器用法示例 ==========" << endl;

    // 1. 创建和初始化pair
    cout << "\n1. 创建和初始化pair:" << endl;

    // 默认初始化
    pair<int, double> p1;
    cout << "默认初始化pair: (" << p1.first << ", " << p1.second << ")" << endl;

    // 使用构造函数初始化
    pair<int, string> p2(1, "Hello");
    cout << "构造函数初始化p2: (" << p2.first << ", \"" << p2.second << "\")" << endl;

    // 使用make_pair创建
    auto p3 = make_pair(2, 3.14);
    cout << "make_pair创建p3: (" << p3.first << ", " << p3.second << ")" << endl;

    // 使用初始化列表（C++11）
    pair<string, int> p4{"Alice", 25};
    cout << "初始化列表p4: (\"" << p4.first << "\", " << p4.second << ")" << endl;

    // 从已有pair复制
    pair<int, string> p5 = p2;
    cout << "复制p2到p5: (" << p5.first << ", \"" << p5.second << "\")" << endl;

    // 2. 访问pair元素
    cout << "\n2. 访问pair元素:" << endl;

    cout << "p2元素访问:" << endl;
    cout << "  p2.first = " << p2.first << endl;
    cout << "  p2.second = \"" << p2.second << "\"" << endl;

    // 修改pair元素
    p2.first = 100;
    p2.second = "Modified";
    cout << "修改后p2: (" << p2.first << ", \"" << p2.second << "\")" << endl;

    // 3. pair比较操作
    cout << "\n3. pair比较操作:" << endl;

    pair<int, string> p6 = make_pair(1, "Apple");
    pair<int, string> p7 = make_pair(2, "Banana");
    pair<int, string> p8 = make_pair(1, "Apple");

    cout << "p6: (1, \"Apple\")" << endl;
    cout << "p7: (2, \"Banana\")" << endl;
    cout << "p8: (1, \"Apple\")" << endl;

    cout << "p6 == p7: " << (p6 == p7 ? "true" : "false") << endl;
    cout << "p6 != p7: " << (p6 != p7 ? "true" : "false") << endl;
    cout << "p6 < p7: " << (p6 < p7 ? "true" : "false") << endl;
    cout << "p6 > p7: " << (p6 > p7 ? "true" : "false") << endl;
    cout << "p6 <= p7: " << (p6 <= p7 ? "true" : "false") << endl;
    cout << "p6 >= p7: " << (p6 >= p7 ? "true" : "false") << endl;
    cout << "p6 == p8: " << (p6 == p8 ? "true" : "false") << endl;

    // 4. 结构化绑定（C++17）
    cout << "\n4. 结构化绑定（C++17）:" << endl;

    auto [key, value] = p4;
    cout << "结构化绑定p4: key=\"" << key << "\", value=" << value << endl;

    // 修改结构化绑定的变量
    key = "Bob";
    value = 30;
    cout << "修改后: key=\"" << key << "\", value=" << value << endl;
    cout << "原始p4未改变: (\"" << p4.first << "\", " << p4.second << ")" << endl;

    // 5. tie解包pair
    cout << "\n5. tie解包pair:" << endl;

    int num;
    string text;

    tie(num, text) = p2;
    cout << "tie解包p2: num=" << num << ", text=\"" << text << "\"" << endl;

    // 使用ignore忽略某个元素
    tie(ignore, text) = p2;
    cout << "使用ignore忽略第一个元素: text=\"" << text << "\"" << endl;

    // 6. swap操作
    cout << "\n6. swap操作:" << endl;

    pair<int, string> p9 = make_pair(10, "Ten");
    pair<int, string> p10 = make_pair(20, "Twenty");

    cout << "交换前:" << endl;
    cout << "  p9: (" << p9.first << ", \"" << p9.second << "\")" << endl;
    cout << "  p10: (" << p10.first << ", \"" << p10.second << "\")" << endl;

    p9.swap(p10);

    cout << "交换后:" << endl;
    cout << "  p9: (" << p9.first << ", \"" << p9.second << "\")" << endl;
    cout << "  p10: (" << p10.first << ", \"" << p10.second << "\")" << endl;

    // 7. 实际应用场景
    cout << "\n7. 实际应用场景:" << endl;

    // 场景1：map的键值对
    cout << "场景1: map的键值对" << endl;

    map<int, string> student_map;
    student_map.insert(make_pair(1, "Alice"));
    student_map.insert(pair<int, string>(2, "Bob"));
    student_map.emplace(3, "Charlie");

    cout << "学生map:" << endl;
    for (const auto& [id, name] : student_map)
    {
        cout << "  学号" << id << ": " << name << endl;
    }

    // 场景2：函数返回两个值
    cout << "\n场景2: 函数返回两个值" << endl;

    auto divide = [](int a, int b) -> pair<bool, double>
    {
        if (b == 0)
        {
            return make_pair(false, 0.0);
        }
        return make_pair(true, static_cast<double>(a) / b);
    };

    auto [success1, result1] = divide(10, 2);
    auto [success2, result2] = divide(10, 0);

    cout << "10 / 2: " << (success1 ? "成功" : "失败") << ", 结果=" << result1 << endl;
    cout << "10 / 0: " << (success2 ? "成功" : "失败") << ", 结果=" << result2 << endl;

    // 场景3：排序和比较
    cout << "\n场景3: 排序和比较" << endl;

    vector<pair<int, string>> items = {{3, "C"}, {1, "A"}, {4, "D"}, {2, "B"}, {5, "E"}};

    cout << "排序前:" << endl;
    for (const auto& item : items)
    {
        cout << "  (" << item.first << ", \"" << item.second << "\")" << endl;
    }

    // 按first排序
    sort(items.begin(), items.end());

    cout << "按first排序后:" << endl;
    for (const auto& item : items)
    {
        cout << "  (" << item.first << ", \"" << item.second << "\")" << endl;
    }

    // 按second排序（使用自定义比较函数）
    sort(items.begin(), items.end(), [](const pair<int, string>& a, const pair<int, string>& b)
         { return a.second < b.second; });

    cout << "按second排序后:" << endl;
    for (const auto& item : items)
    {
        cout << "  (" << item.first << ", \"" << item.second << "\")" << endl;
    }

    // 8. pair与tuple的关系
    cout << "\n8. pair与tuple的关系:" << endl;

    // pair可以看作是tuple的特例（两个元素）
    pair<int, string> p11 = make_pair(42, "Answer");

    // 将pair转换为tuple
    tuple<int, string> t11 = p11;
    cout << "pair转换为tuple: (" << get<0>(t11) << ", \"" << get<1>(t11) << "\")" << endl;

    // 从tuple创建pair（需要元素数量匹配）
    tuple<int, string> t12 = make_tuple(100, "Hundred");
    pair<int, string> p12 = make_pair(get<0>(t12), get<1>(t12));
    cout << "tuple转换为pair: (" << p12.first << ", \"" << p12.second << "\")" << endl;

    // 9. 嵌套pair
    cout << "\n9. 嵌套pair:" << endl;

    // pair的元素可以是另一个pair
    pair<int, pair<string, double>> nested_pair = make_pair(1, make_pair("Pi", 3.14159));

    cout << "嵌套pair: (" << nested_pair.first << ", (\"" << nested_pair.second.first << "\", "
         << nested_pair.second.second << "))" << endl;

    // 使用结构化绑定访问嵌套pair
    auto [id, inner_pair] = nested_pair;
    auto [name, value_pi] = inner_pair;
    cout << "结构化绑定访问: id=" << id << ", name=\"" << name << "\", value=" << value_pi << endl;

    // 10. 性能提示
    cout << "\n10. 性能提示:" << endl;
    cout << "1. pair是轻量级结构，访问效率高" << endl;
    cout << "2. make_pair会自动推导类型，比显式构造函数更方便" << endl;
    cout << "3. 结构化绑定（C++17）提供了更简洁的语法" << endl;
    cout << "4. pair的比较是字典序比较（先比较first，再比较second）" << endl;
    cout << "5. 对于复杂数据结构，考虑使用结构体而不是嵌套pair" << endl;
    cout << "6. 在map中使用时，pair作为value_type" << endl;

    // 11. 常见错误和注意事项
    cout << "\n11. 常见错误和注意事项:" << endl;
    cout << "1. 注意pair的比较规则：先比较first，相等时再比较second" << endl;
    cout << "2. make_pair会自动推导类型，可能不是期望的类型" << endl;
    cout << "3. 结构化绑定是C++17特性，需要编译器支持" << endl;
    cout << "4. pair的swap操作交换两个pair的所有元素" << endl;
    cout << "5. 在算法中使用pair时，注意比较函数的实现" << endl;

    // 12. 更多示例
    cout << "\n12. 更多示例:" << endl;

    // 使用pair实现简单二维点
    cout << "使用pair表示二维点:" << endl;

    using Point = pair<double, double>;
    Point p13 = make_pair(1.0, 2.0);
    Point p14 = make_pair(3.0, 4.0);

    // 计算两点距离
    auto distance = [](const Point& a, const Point& b)
    {
        double dx = a.first - b.first;
        double dy = a.second - b.second;
        return sqrt(dx * dx + dy * dy);
    };

    cout << "点p13: (" << p13.first << ", " << p13.second << ")" << endl;
    cout << "点p14: (" << p14.first << ", " << p14.second << ")" << endl;
    cout << "两点距离: " << distance(p13, p14) << endl;

    // pair数组
    cout << "\npair数组示例:" << endl;

    pair<int, string> pairs[] = {{1, "One"}, {2, "Two"}, {3, "Three"}, {4, "Four"}, {5, "Five"}};

    cout << "数字对应表:" << endl;
    for (const auto& p : pairs)
    {
        cout << "  " << p.first << " -> \"" << p.second << "\"" << endl;
    }

    cout << "\n========== pair示例结束 ==========" << endl;

    return 0;
}
