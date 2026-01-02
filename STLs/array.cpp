/**
 * @file array.cpp
 * @brief array容器用法示例
 * 
 * array是C++标准模板库(STL)中的固定大小数组容器
 * 特点：
 * 1. 固定大小：编译时确定大小，运行时不能改变
 * 2. 连续存储：元素在内存中连续存储，缓存友好
 * 3. 随机访问：支持O(1)时间的随机访问
 * 4. 栈上分配：通常分配在栈上，性能高效
 * 5. 已知大小：编译时已知大小，支持编译时检查
 * 
 * 常用操作时间复杂度：
 * - 访问元素：O(1)
 * - 遍历元素：O(n)
 * - 查找元素：O(n)（线性查找）
 * 
 * 与普通数组的比较：
 * 1. 提供STL接口：支持迭代器、算法等
 * 2. 知道自身大小：通过size()方法获取
 * 3. 不会退化为指针：传递时不会丢失大小信息
 * 4. 支持赋值：可以进行容器间的赋值操作
 */

#include <iostream>
#include <array>
#include <algorithm>
#include <vector>

using namespace std;

int main() {
    cout << "========== array容器用法示例 ==========" << endl;
    
    // 1. 创建和初始化array
    cout << "\n1. 创建和初始化array:" << endl;
    
    // 默认初始化（元素值未定义）
    array<int, 5> arr1;
    cout << "默认初始化arr1大小: " << arr1.size() << endl;
    
    // 值初始化（所有元素初始化为0）
    array<int, 5> arr2 = {};
    cout << "值初始化arr2: ";
    for (int num : arr2) cout << num << " ";
    cout << endl;
    
    // 使用初始化列表
    array<int, 5> arr3 = {1, 2, 3, 4, 5};
    cout << "arr3: ";
    for (int num : arr3) cout << num << " ";
    cout << endl;
    
    // 部分初始化（剩余元素初始化为0）
    array<int, 5> arr4 = {10, 20, 30};
    cout << "部分初始化arr4: ";
    for (int num : arr4) cout << num << " ";
    cout << endl;
    
    // 统一初始化（C++11）
    array<int, 5> arr5{100, 200, 300, 400, 500};
    cout << "统一初始化arr5: ";
    for (int num : arr5) cout << num << " ";
    cout << endl;
    
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;
    
    // 访问元素
    cout << "arr3[2] = " << arr3[2] << endl;           // 随机访问
    cout << "arr3.at(2) = " << arr3.at(2) << endl;     // 带边界检查
    cout << "arr3.front() = " << arr3.front() << endl; // 第一个元素
    cout << "arr3.back() = " << arr3.back() << endl;   // 最后一个元素
    
    // 使用data()获取底层指针
    int* ptr = arr3.data();
    cout << "arr3.data()[3] = " << ptr[3] << endl;
    
    // 3. 遍历array
    cout << "\n3. 遍历array:" << endl;
    
    cout << "使用范围for循环遍历arr3:" << endl;
    cout << "  ";
    for (int num : arr3) {
        cout << num << " ";
    }
    cout << endl;
    
    cout << "使用迭代器遍历arr3:" << endl;
    cout << "  ";
    for (auto it = arr3.begin(); it != arr3.end(); ++it) {
        cout << *it << " ";
    }
    cout << endl;
    
    cout << "使用反向迭代器遍历arr3:" << endl;
    cout << "  ";
    for (auto rit = arr3.rbegin(); rit != arr3.rend(); ++rit) {
        cout << *rit << " ";
    }
    cout << endl;
    
    cout << "使用下标遍历arr3:" << endl;
    cout << "  ";
    for (size_t i = 0; i < arr3.size(); i++) {
        cout << arr3[i] << " ";
    }
    cout << endl;
    
    // 4. 容量操作
    cout << "\n4. 容量操作:" << endl;
    
    cout << "arr3大小: " << arr3.size() << endl;
    cout << "arr3最大大小: " << arr3.max_size() << endl;
    cout << "arr3是否为空: " << (arr3.empty() ? "是" : "否") << endl;
    
    // 注意：array大小固定，没有resize()、reserve()等方法
    
    // 5. 修改操作
    cout << "\n5. 修改操作:" << endl;
    
    // 填充元素
    arr1.fill(99);
    cout << "fill(99)后arr1: ";
    for (int num : arr1) cout << num << " ";
    cout << endl;
    
    // 交换两个array
    array<int, 5> arr6 = {1, 2, 3, 4, 5};
    array<int, 5> arr7 = {10, 20, 30, 40, 50};
    
    cout << "交换前:" << endl;
    cout << "  arr6: ";
    for (int num : arr6) cout << num << " ";
    cout << endl;
    cout << "  arr7: ";
    for (int num : arr7) cout << num << " ";
    cout << endl;
    
    arr6.swap(arr7);
    
    cout << "交换后:" << endl;
    cout << "  arr6: ";
    for (int num : arr6) cout << num << " ";
    cout << endl;
    cout << "  arr7: ";
    for (int num : arr7) cout << num << " ";
    cout << endl;
    
    // 6. 算法应用
    cout << "\n6. 算法应用:" << endl;
    
    array<int, 8> arr8 = {5, 3, 8, 1, 9, 2, 7, 4};
    
    cout << "原始arr8: ";
    for (int num : arr8) cout << num << " ";
    cout << endl;
    
    // 排序
    sort(arr8.begin(), arr8.end());
    cout << "排序后arr8: ";
    for (int num : arr8) cout << num << " ";
    cout << endl;
    
    // 查找
    auto it = find(arr8.begin(), arr8.end(), 7);
    if (it != arr8.end()) {
        cout << "找到元素7，位置: " << distance(arr8.begin(), it) << endl;
    }
    
    // 反转
    reverse(arr8.begin(), arr8.end());
    cout << "反转后arr8: ";
    for (int num : arr8) cout << num << " ";
    cout << endl;
    
    // 累加
    int sum = 0;
    for (int num : arr8) sum += num;
    cout << "arr8元素和: " << sum << endl;
    
    // 7. 多维array
    cout << "\n7. 多维array:" << endl;
    
    // 二维array
    array<array<int, 3>, 2> matrix = {{
        {1, 2, 3},
        {4, 5, 6}
    }};
    
    cout << "二维array矩阵:" << endl;
    for (const auto& row : matrix) {
        for (int num : row) {
            cout << num << " ";
        }
        cout << endl;
    }
    
    // 三维array
    array<array<array<int, 2>, 2>, 2> cube = {{
        {{{{1, 2}}, {{3, 4}}}},
        {{{{5, 6}}, {{7, 8}}}}
    }};
    
    cout << "三维array立方体:" << endl;
    for (const auto& layer : cube) {
        for (const auto& row : layer) {
            for (int num : row) {
                cout << num << " ";
            }
            cout << "  ";
        }
        cout << endl;
    }
    
    // 8. 与普通数组的比较
    cout << "\n8. 与普通数组的比较:" << endl;
    
    // 普通C数组
    int c_array[5] = {1, 2, 3, 4, 5};
    
    // STL array
    array<int, 5> stl_array = {1, 2, 3, 4, 5};
    
    cout << "普通数组大小: " << sizeof(c_array) / sizeof(c_array[0]) << endl;
    cout << "STL array大小: " << stl_array.size() << endl;
    
    // 普通数组传递时会退化为指针，丢失大小信息
    // STL array传递时保持完整类型信息
    
    // 9. 实际应用场景
    cout << "\n9. 实际应用场景:" << endl;
    
    // 场景1：固定大小的缓冲区
    cout << "场景1: 固定大小的缓冲区" << endl;
    const size_t BUFFER_SIZE = 1024;
    array<char, BUFFER_SIZE> buffer;
    
    // 模拟填充缓冲区
    for (size_t i = 0; i < 10; i++) {
        buffer[i] = 'A' + i;
    }
    buffer[10] = '\0';
    
    cout << "缓冲区内容: " << buffer.data() << endl;
    cout << "缓冲区大小: " << buffer.size() << "字节" << endl;
    
    // 场景2：查找表（Lookup Table）
    cout << "\n场景2: 查找表（Lookup Table）" << endl;
    
    // 月份天数查找表
    array<int, 12> month_days = {31, 28, 31, 30, 31, 30,
                                 31, 31, 30, 31, 30, 31};
    
    cout << "月份天数查找表:" << endl;
    for (size_t i = 0; i < month_days.size(); i++) {
        cout << "  月份" << (i + 1) << ": " << month_days[i] << "天" << endl;
    }
    
    // 场景3：游戏开发中的固定大小数组
    cout << "\n场景3: 游戏开发中的固定大小数组" << endl;
    
    // 玩家得分（固定4个玩家）
    array<int, 4> player_scores = {0, 0, 0, 0};
    
    // 模拟游戏得分
    player_scores[0] += 100;
    player_scores[1] += 150;
    player_scores[2] += 80;
    player_scores[3] += 200;
    
    cout << "玩家得分:" << endl;
    for (size_t i = 0; i < player_scores.size(); i++) {
        cout << "  玩家" << (i + 1) << ": " << player_scores[i] << "分" << endl;
    }
    
    // 10. 性能提示
    cout << "\n10. 性能提示:" << endl;
    cout << "1. array在栈上分配，访问速度快，但大小有限" << endl;
    cout << "2. 编译时已知大小，编译器可以进行更多优化" << endl;
    cout << "3. 适合小型、固定大小的数据集合" << endl;
    cout << "4. 如果需要动态大小，使用vector" << endl;
    cout << "5. array的迭代器是随机访问迭代器，支持所有STL算法" << endl;
    cout << "6. array不会退化为指针，类型安全更好" << endl;
    
    // 11. 与vector的比较
    cout << "\n11. array与vector的比较:" << endl;
    cout << "1. 大小: array固定，vector动态" << endl;
    cout << "2. 内存分配: array栈上，vector堆上" << endl;
    cout << "3. 性能: array访问更快，vector更灵活" << endl;
    cout << "4. 适用场景: array适合小型固定数据，vector适合大型动态数据" << endl;
    
    cout << "\n========== array示例结束 ==========" << endl;
    
    return 0;
}
