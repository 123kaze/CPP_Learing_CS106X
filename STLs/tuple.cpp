/**
 * @file tuple.cpp
 * @brief tuple容器用法示例
 *
 * tuple是C++标准模板库(STL)中的元组容器
 * 特点：
 * 1. 固定大小：编译时确定大小，运行时不能改变
 * 2. 异构元素：可以存储不同类型的元素
 * 3. 值语义：tuple是值类型，可以复制和赋值
 * 4. 结构化绑定：C++17支持结构化绑定，方便访问元素
 *
 * 常用操作：
 * - 创建tuple：make_tuple, tuple构造函数
 * - 访问元素：get<index>(tuple), tie, structured binding
 * - 比较操作：==, !=, <, >, <=, >=
 * - 其他操作：tuple_size, tuple_element, swap
 */

#include <algorithm>
#include <iostream>
#include <string>
#include <tuple>
#include <vector>

using namespace std;

int main()
{
    cout << "========== tuple容器用法示例 ==========" << endl;

    // 1. 创建和初始化tuple
    cout << "\n1. 创建和初始化tuple:" << endl;

    // 默认初始化
    tuple<int, double, string> t1;
    cout << "默认初始化tuple大小: " << tuple_size<decltype(t1)>::value << endl;

    // 使用构造函数初始化
    tuple<int, double, string> t2(1, 3.14, "Hello");
    cout << "构造函数初始化t2: (" << get<0>(t2) << ", " << get<1>(t2) << ", \"" << get<2>(t2)
         << "\")" << endl;

    // 使用make_tuple创建
    auto t3 = make_tuple(2, 2.718, "World");

    auto nums(tuple_size<decltype(t1)>::value);
    cout << nums << endl;

    cout << "make_tuple创建t3: (" << get<0>(t3) << ", " << get<1>(t3) << ", \"" << get<2>(t3)
         << "\")" << endl;

    // 使用初始化列表（C++11）
    tuple<int, double, string> t4{3, 1.618, "Tuple"};
    cout << "初始化列表t4: (" << get<0>(t4) << ", " << get<1>(t4) << ", \"" << get<2>(t4) << "\")"
         << endl;

    // 2. 访问tuple元素
    cout << "\n2. 访问tuple元素:" << endl;

    // 使用get<index>访问
    cout << "t2元素访问:" << endl;
    cout << "  get<0>(t2) = " << get<0>(t2) << endl;
    cout << "  get<1>(t2) = " << get<1>(t2) << endl;
    cout << "  get<2>(t2) = " << get<2>(t2) << endl;

    // 使用get<type>访问（类型必须唯一）
    cout << "使用类型访问:" << endl;
    cout << "  get<int>(t2) = " << get<int>(t2) << endl;
    cout << "  get<double>(t2) = " << get<double>(t2) << endl;
    cout << "  get<string>(t2) = " << get<string>(t2) << endl;

    // 3. 结构化绑定（C++17）
    cout << "\n3. 结构化绑定（C++17）:" << endl;

    auto [x, y, z] = t2;
    cout << "结构化绑定t2: x=" << x << ", y=" << y << ", z=\"" << z << "\"" << endl;

    // 修改结构化绑定的变量
    x = 100;
    y = 9.99;
    z = "Modified";
    cout << "修改后: x=" << x << ", y=" << y << ", z=\"" << z << "\"" << endl;
    cout << "原始t2未改变: (" << get<0>(t2) << ", " << get<1>(t2) << ", \"" << get<2>(t2) << "\")"
         << endl;

    // 4. tie解包tuple
    cout << "\n4. tie解包tuple:" << endl;

    int a;
    double b;
    string c;

    tie(a, b, c) = t2;
    cout << "tie解包t2: a=" << a << ", b=" << b << ", c=\"" << c << "\"" << endl;

    // 使用ignore忽略某些元素
    tie(a, ignore, c) = t2;
    cout << "使用ignore忽略第二个元素: a=" << a << ", c=\"" << c << "\"" << endl;

    // 5. tuple比较操作
    cout << "\n5. tuple比较操作:" << endl;

    tuple<int, string> t5 = make_tuple(1, "Apple");
    tuple<int, string> t6 = make_tuple(2, "Banana");
    tuple<int, string> t7 = make_tuple(1, "Apple");

    cout << "t5: (1, \"Apple\")" << endl;
    cout << "t6: (2, \"Banana\")" << endl;
    cout << "t7: (1, \"Apple\")" << endl;

    cout << "t5 == t6: " << (t5 == t6 ? "true" : "false") << endl;
    cout << "t5 != t6: " << (t5 != t6 ? "true" : "false") << endl;
    cout << "t5 < t6: " << (t5 < t6 ? "true" : "false") << endl;
    cout << "t5 > t6: " << (t5 > t6 ? "true" : "false") << endl;
    cout << "t5 == t7: " << (t5 == t7 ? "true" : "false") << endl;

    // 6. tuple连接和拆分
    cout << "\n6. tuple连接和拆分:" << endl;

    // 使用tuple_cat连接多个tuple
    auto t8 = make_tuple(1, "Hello");
    auto t9 = make_tuple(3.14, 'A');
    auto t10 = tuple_cat(t8, t9);

    cout << "连接tuple: tuple_cat((1, \"Hello\"), (3.14, 'A'))" << endl;
    cout << "结果: (" << get<0>(t10) << ", \"" << get<1>(t10) << "\", " << get<2>(t10) << ", '"
         << get<3>(t10) << "')" << endl;

    // 7. tuple_size和tuple_element
    cout << "\n7. tuple_size和tuple_element:" << endl;

    cout << "t10的大小: " << tuple_size<decltype(t10)>::value << endl;

    // 获取tuple元素类型
    using elem0_type = tuple_element<0, decltype(t10)>::type;
    using elem1_type = tuple_element<1, decltype(t10)>::type;
    using elem2_type = tuple_element<2, decltype(t10)>::type;
    using elem3_type = tuple_element<3, decltype(t10)>::type;

    cout << "t10元素类型:" << endl;
    cout << "  索引0: " << typeid(elem0_type).name() << " (int)" << endl;
    cout << "  索引1: " << typeid(elem1_type).name() << " (const char*)" << endl;
    cout << "  索引2: " << typeid(elem2_type).name() << " (double)" << endl;
    cout << "  索引3: " << typeid(elem3_type).name() << " (char)" << endl;

    // 8. 实际应用场景
    cout << "\n8. 实际应用场景:" << endl;

    // 场景1：函数返回多个值
    cout << "场景1: 函数返回多个值" << endl;

    auto get_student_info = [](int id) -> tuple<string, int, double>
    {
        if (id == 1) return make_tuple("Alice", 20, 85.5);
        if (id == 2) return make_tuple("Bob", 21, 90.0);
        if (id == 3) return make_tuple("Charlie", 22, 78.5);
        return make_tuple("Unknown", 0, 0.0);
    };

    auto student1 = get_student_info(1);
    cout << "学生1信息: 姓名=" << get<0>(student1) << ", 年龄=" << get<1>(student1)
         << ", 分数=" << get<2>(student1) << endl;

    // 使用结构化绑定
    auto [name, age, score] = get_student_info(2);
    cout << "学生2信息: 姓名=" << name << ", 年龄=" << age << ", 分数=" << score << endl;

    // 场景2：多值比较
    cout << "\n场景2: 多值比较（版本号比较）" << endl;

    auto compare_versions = [](tuple<int, int, int> v1, tuple<int, int, int> v2)
    {
        if (v1 < v2) return -1;
        if (v1 > v2) return 1;
        return 0;
    };

    tuple<int, int, int> version1 = make_tuple(1, 2, 3);
    tuple<int, int, int> version2 = make_tuple(1, 3, 0);

    int result = compare_versions(version1, version2);
    cout << "版本比较: v1=" << get<0>(version1) << "." << get<1>(version1) << "."
         << get<2>(version1) << " vs v2=" << get<0>(version2) << "." << get<1>(version2) << "."
         << get<2>(version2) << endl;
    cout << "比较结果: "
         << (result == -1  ? "v1 < v2"
             : result == 1 ? "v1 > v2"
                           : "v1 == v2")
         << endl;

    // 场景3：数据分组
    cout << "\n场景3: 数据分组" << endl;

    vector<tuple<string, int, string>> employees = {
        make_tuple("Alice", 25, "Engineering"), make_tuple("Bob", 30, "Sales"),
        make_tuple("Charlie", 28, "Engineering"), make_tuple("David", 35, "Marketing"),
        make_tuple("Eve", 26, "Engineering")};

    cout << "员工列表:" << endl;
    for (const auto& [emp_name, emp_age, emp_dept] : employees)
    {
        cout << "  姓名: " << emp_name << ", 年龄: " << emp_age << ", 部门: " << emp_dept << endl;
    }

    // 按部门统计
    cout << "\n按部门统计员工数:" << endl;
    // 简化统计，实际应用中可能需要使用map
    int eng_count = 0, sales_count = 0, marketing_count = 0;
    for (const auto& emp : employees)
    {
        if (get<2>(emp) == "Engineering")
            eng_count++;
        else if (get<2>(emp) == "Sales")
            sales_count++;
        else if (get<2>(emp) == "Marketing")
            marketing_count++;
    }
    cout << "  工程部: " << eng_count << "人" << endl;
    cout << "  销售部: " << sales_count << "人" << endl;
    cout << "  市场部: " << marketing_count << "人" << endl;

    // 9. 与pair的比较
    cout << "\n9. tuple与pair的比较:" << endl;

    cout << "相似点:" << endl;
    cout << "  1. 都是值类型，可以复制和赋值" << endl;
    cout << "  2. 都支持比较操作" << endl;
    cout << "  3. 都可以存储异构数据" << endl;

    cout << "\n不同点:" << endl;
    cout << "  1. tuple可以存储任意数量的元素，pair只能存储2个" << endl;
    cout << "  2. pair有first和second成员，tuple使用get访问" << endl;
    cout << "  3. pair有make_pair辅助函数，tuple有make_tuple" << endl;
    cout << "  4. tuple支持结构化绑定，pair也支持" << endl;

    // 10. 性能提示
    cout << "\n10. 性能提示:" << endl;
    cout << "1. tuple是编译时确定的结构，访问效率高" << endl;
    cout << "2. 结构化绑定（C++17）提供了更简洁的语法" << endl;
    cout << "3. 对于固定数量的异构数据，tuple比自定义结构体更灵活" << endl;
    cout << "4. 如果需要命名成员，考虑使用结构体而不是tuple" << endl;
    cout << "5. tuple的比较操作是字典序比较" << endl;
    cout << "6. 使用tie可以方便地从tuple提取值到现有变量" << endl;

    // 11. 高级用法
    cout << "\n11. 高级用法:" << endl;

    // 递归tuple处理
    cout << "递归处理tuple元素（简化版）:" << endl;

    // 简化版：手动打印tuple元素
    auto print_tuple_simple = [](const auto& tup)
    {
        cout << "  (";
        constexpr size_t size = tuple_size<remove_reference_t<decltype(tup)>>::value;
        if constexpr (size > 0)
        {
            cout << get<0>(tup);
            if constexpr (size > 1)
            {
                cout << ", " << get<1>(tup);
                if constexpr (size > 2)
                {
                    cout << ", " << get<2>(tup);
                    if constexpr (size > 3)
                    {
                        cout << ", " << get<3>(tup);
                        if constexpr (size > 4)
                        {
                            cout << ", " << get<4>(tup);
                        }
                    }
                }
            }
        }
        cout << ")" << endl;
    };

    auto complex_tuple = make_tuple(42, "Test", 3.14, 'X', true);
    cout << "复杂tuple: ";
    print_tuple_simple(complex_tuple);

    // 12. 常见错误和注意事项
    cout << "\n12. 常见错误和注意事项:" << endl;
    cout << "1. 访问不存在的索引会导致编译错误" << endl;
    cout << "2. 使用get<type>时类型必须唯一" << endl;
    cout << "3. tuple的比较是字典序，需要所有元素都支持比较" << endl;
    cout << "4. 结构化绑定是C++17特性，需要编译器支持" << endl;
    cout << "5. tie创建的是引用，修改tie的变量不会影响原始tuple" << endl;

    cout << "\n========== tuple示例结束 ==========" << endl;

    return 0;
}
