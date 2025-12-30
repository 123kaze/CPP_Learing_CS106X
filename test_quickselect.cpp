#include <iostream>
#include <vector>
#include <algorithm>
#include "Sort_Methods/Quick.h"
using namespace std;

// 当前有问题的quickSelect实现
int quickSelect(vector<int>& a, int left, int right, int k)
{
    if (left == right)  // 只有一个元素
        return a[left];
    
    // 分区
    int pivotIndex = partition(a, left, right);
    
    // pivotIndex就是pivot在排序后的正确位置
    if (k == pivotIndex)
        return a[pivotIndex];  // 找到了第k小的元素
    else if (k < pivotIndex)
        return quickSelect(a, left, pivotIndex - 1, k);  // 在左半部分找
    else
        return quickSelect(a, pivotIndex + 1, right, k);  // 在右半部分找
}

int findKthSmallest(vector<int>& nums, int k)
{
    if (k < 0 || k >= nums.size())
    {
        cout << "Error: k out of range!" << endl;
        return -1;
    }
    
    // 注意：quickSelect会修改原数组
    return quickSelect(nums, 0, nums.size() - 1, k);
}

// 测试函数
void testQuickSelect() {
    cout << "测试快速选择算法：" << endl;
    
    // 测试用例1：简单数组
    {
        vector<int> arr = {3, 2, 1, 5, 4};
        vector<int> arrCopy = arr;
        
        cout << "\n数组: ";
        for (int num : arr) cout << num << " ";
        cout << endl;
        
        for (int k = 0; k < arr.size(); k++) {
            vector<int> testArr = arrCopy;
            int result = findKthSmallest(testArr, k);
            sort(arrCopy.begin(), arrCopy.end());
            int expected = arrCopy[k];
            
            cout << "第" << k << "小元素: 结果=" << result << ", 期望=" << expected;
            if (result == expected) {
                cout << " ✓" << endl;
            } else {
                cout << " ✗" << endl;
            }
        }
    }
    
    // 测试用例2：有重复元素的数组
    {
        vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
        vector<int> arrCopy = arr;
        
        cout << "\n数组(有重复): ";
        for (int num : arr) cout << num << " ";
        cout << endl;
        
        for (int k = 0; k < min(5, (int)arr.size()); k++) {
            vector<int> testArr = arrCopy;
            int result = findKthSmallest(testArr, k);
            sort(arrCopy.begin(), arrCopy.end());
            int expected = arrCopy[k];
            
            cout << "第" << k << "小元素: 结果=" << result << ", 期望=" << expected;
            if (result == expected) {
                cout << " ✓" << endl;
            } else {
                cout << " ✗" << endl;
            }
        }
    }
    
    // 测试用例3：边界情况
    {
        vector<int> arr = {42};
        cout << "\n单元素数组: ";
        for (int num : arr) cout << num << " ";
        cout << endl;
        
        int result = findKthSmallest(arr, 0);
        cout << "第0小元素: 结果=" << result << ", 期望=42";
        if (result == 42) {
            cout << " ✓" << endl;
        } else {
            cout << " ✗" << endl;
        }
    }
}

int main() {
    testQuickSelect();
    return 0;
}
