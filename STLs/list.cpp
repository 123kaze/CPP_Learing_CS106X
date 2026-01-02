/**
 * @file list.cpp
 * @brief list容器用法示例
 * 
 * list是C++标准模板库(STL)中的双向链表容器
 * 特点：
 * 1. 双向链表：每个元素包含指向前后元素的指针
 * 2. 非连续存储：元素在内存中非连续存储
 * 3. 插入删除高效：在任何位置插入/删除元素都是O(1)时间复杂度
 * 4. 不支持随机访问：只能通过迭代器顺序访问
 * 
 * 常用操作时间复杂度：
 * - 插入/删除元素：O(1)
 * - 访问元素：O(n)（需要遍历）
 * - 查找：O(n)
 * - 排序：O(n log n)
 */

#include <iostream>
#include <list>
#include <algorithm>

using namespace std;

int main() {
    cout << "========== list容器用法示例 ==========" << endl;
    
    // 1. 创建和初始化list
    cout << "\n1. 创建和初始化list:" << endl;
    
    // 空list
    list<int> lst1;
    cout << "空list大小: " << lst1.size() << endl;
    
    // 指定大小和初始值
    list<int> lst2(5, 10);  // 5个元素，每个都是10
    cout << "lst2: ";
    for (int num : lst2) cout << num << " ";
    cout << endl;
    
    // 使用初始化列表
    list<int> lst3 = {1, 2, 3, 4, 5};
    cout << "lst3: ";
    for (int num : lst3) cout << num << " ";
    cout << endl;
    
    // 从数组初始化
    int arr[] = {6, 7, 8, 9, 10};
    list<int> lst4(arr, arr + 5);
    cout << "lst4: ";
    for (int num : lst4) cout << num << " ";
    cout << endl;
    
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;
    
    // 添加元素
    lst1.push_back(100);    // 尾部添加
    lst1.push_front(50);    // 头部添加
    lst1.push_back(200);
    cout << "添加元素后lst1: ";
    for (int num : lst1) cout << num << " ";
    cout << endl;
    
    // 访问元素
    cout << "lst3.front() = " << lst3.front() << endl; // 第一个元素
    cout << "lst3.back() = " << lst3.back() << endl;   // 最后一个元素
    
    // 3. 插入和删除操作
    cout << "\n3. 插入和删除操作:" << endl;
    
    // 在指定位置插入
    auto it = lst3.begin();
    advance(it, 2);  // 移动到第3个位置
    lst3.insert(it, 99);
    cout << "在位置2插入99后lst3: ";
    for (int num : lst3) cout << num << " ";
    cout << endl;
    
    // 删除指定位置元素
    it = lst3.begin();
    advance(it, 2);
    lst3.erase(it);
    cout << "删除位置2元素后lst3: ";
    for (int num : lst3) cout << num << " ";
    cout << endl;
    
    // 删除头部和尾部元素
    lst3.pop_front();
    lst3.pop_back();
    cout << "pop_front和pop_back后lst3: ";
    for (int num : lst3) cout << num << " ";
    cout << endl;
    
    // 4. 特殊操作（list特有）
    cout << "\n4. list特有操作:" << endl;
    
    // splice：将一个list的元素移动到另一个list
    list<int> lst5 = {100, 200, 300};
    list<int> lst6 = {400, 500, 600};
    
    auto it5 = lst5.begin();
    advance(it5, 1);  // 指向lst5的第二个元素
    
    // 将lst6的所有元素移动到lst5的第二个位置之前
    lst5.splice(it5, lst6);
    cout << "splice后lst5: ";
    for (int num : lst5) cout << num << " ";
    cout << endl;
    cout << "splice后lst6大小: " << lst6.size() << endl;
    
    // merge：合并两个已排序的list
    list<int> lst7 = {1, 3, 5};
    list<int> lst8 = {2, 4, 6};
    lst7.merge(lst8);
    cout << "merge后lst7: ";
    for (int num : lst7) cout << num << " ";
    cout << endl;
    
    // sort：排序（list有自己的sort方法，比std::sort更高效）
    list<int> lst9 = {5, 3, 8, 1, 9, 2};
    lst9.sort();
    cout << "排序后lst9: ";
    for (int num : lst9) cout << num << " ";
    cout << endl;
    
    // reverse：反转
    lst9.reverse();
    cout << "反转后lst9: ";
    for (int num : lst9) cout << num << " ";
    cout << endl;
    
    // unique：去除连续重复元素
    list<int> lst10 = {1, 1, 2, 2, 3, 3, 3, 4, 5, 5};
    lst10.unique();
    cout << "unique后lst10: ";
    for (int num : lst10) cout << num << " ";
    cout << endl;
    
    // 5. 迭代器使用
    cout << "\n5. 迭代器使用:" << endl;
    
    cout << "使用迭代器遍历lst4: ";
    for (list<int>::iterator it = lst4.begin(); it != lst4.end(); ++it) {
        cout << *it << " ";
    }
    cout << endl;
    
    cout << "使用反向迭代器遍历lst4: ";
    for (list<int>::reverse_iterator rit = lst4.rbegin(); rit != lst4.rend(); ++rit) {
        cout << *rit << " ";
    }
    cout << endl;
    
    // 6. 容量操作
    cout << "\n6. 容量操作:" << endl;
    
    cout << "lst3大小: " << lst3.size() << endl;
    cout << "lst3是否为空: " << (lst3.empty() ? "是" : "否") << endl;
    
    // 调整大小
    lst3.resize(8, 0);  // 调整大小为8，新增元素初始化为0
    cout << "调整大小后lst3: ";
    for (int num : lst3) cout << num << " ";
    cout << endl;
    
    // 清空list
    list<int> lst11 = {1, 2, 3, 4, 5};
    lst11.clear();
    cout << "清空后lst11大小: " << lst11.size() << endl;
    
    // 7. 算法应用
    cout << "\n7. 算法应用:" << endl;
    
    list<int> lst12 = {5, 3, 8, 1, 9, 2};
    
    // 查找
    auto find_it = find(lst12.begin(), lst12.end(), 8);
    if (find_it != lst12.end()) {
        cout << "找到元素8" << endl;
    }
    
    // 计数
    int count_3 = count(lst12.begin(), lst12.end(), 3);
    cout << "元素3出现的次数: " << count_3 << endl;
    
    // 8. 性能提示
    cout << "\n8. 性能提示:" << endl;
    cout << "1. 如果需要频繁在任意位置插入/删除元素，list是最佳选择" << endl;
    cout << "2. list不支持随机访问，如果需要随机访问请使用vector或deque" << endl;
    cout << "3. list的每个元素需要额外存储前后指针，内存开销较大" << endl;
    cout << "4. list的迭代器在插入/删除操作后不会失效（除非删除当前元素）" << endl;
    cout << "5. 对list排序使用list::sort()而不是std::sort()，效率更高" << endl;
    
    cout << "\n========== list示例结束 ==========" << endl;
    
    return 0;
}
