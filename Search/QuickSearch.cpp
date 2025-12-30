#include <iostream>
#include <vector>
#include <algorithm>
#include "../Sort_Methods/Quick.h"
using namespace std;

/**
 * @brief 快速选择算法 - 查找数组中第k小的元素 (0-based索引)
 * 
 * @param a 数组引用（会被修改）
 * @param left 搜索左边界
 * @param right 搜索右边界
 * @param k 要查找的第k小的元素索引 (0-based)
 * @return int 第k小的元素值
 */
int quickSelect(vector<int>& a, int left, int right, int k)
{
    // 递归终止条件：只有一个元素
    if (left == right) {
        return a[left];
    }
    
    // 分区操作
    int pivotIndex = partition(a, left, right);
    
    // 根据pivot位置决定下一步
    if (k == pivotIndex) {
        return a[pivotIndex];  // 找到了第k小的元素
    } else if (k < pivotIndex) {
        return quickSelect(a, left, pivotIndex - 1, k);  // 在左半部分找
    } else {
        return quickSelect(a, pivotIndex + 1, right, k);  // 在右半部分找
    }
}

/**
 * @brief 查找数组中第k小的元素 (0-based索引)
 * 
 * @param nums 数组（会被修改）
 * @param k 要查找的第k小的元素索引 (0-based)
 * @return int 第k小的元素值，如果k超出范围返回-1
 */
int findKthSmallest(vector<int>& nums, int k)
{
    if (k < 0 || k >= (int)nums.size())
    {
        cerr << "错误: k=" << k << " 超出范围 [0, " << nums.size() - 1 << "]" << endl;
        return -1;
    }
    
    // quickSelect会修改原数组
    return quickSelect(nums, 0, nums.size() - 1, k);
}

/**
 * @brief 查找数组中第k小的元素 (1-based索引，更符合直觉)
 * 
 * @param nums 数组（会被修改）
 * @param k 要查找的第k小的元素 (1-based: 第1小，第2小，...)
 * @return int 第k小的元素值，如果k超出范围返回-1
 */
int findKthSmallestOneBased(vector<int>& nums, int k)
{
    if (k < 1 || k > (int)nums.size())
    {
        cerr << "错误: k=" << k << " 超出范围 [1, " << nums.size() << "]" << endl;
        return -1;
    }
    
    // 转换为0-based索引
    return findKthSmallest(nums, k - 1);
}
