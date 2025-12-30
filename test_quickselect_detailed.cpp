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

// 打印数组
void printArray(const vector<int>& arr, const string& label = "") {
    if (!label.empty()) cout << label << ": ";
    for (int num : arr) cout << num << " ";
    cout << endl;
}

// 详细测试：跟踪递归过程
void detailedTest() {
    cout << "=== 详细测试快速选择算法 ===" << endl;
    
    // 测试一个可能暴露问题的数组
    vector<int> arr = {7, 10, 4, 3, 20, 15};
    vector<int> arrCopy = arr;
    
    cout << "\n原始数组: ";
    printArray(arr);
    
    sort(arrCopy.begin(), arrCopy.end());
    cout << "排序后数组: ";
    printArray(arrCopy);
    
    cout << "\n查找第k小元素 (0-based索引):" << endl;
    for (int k = 0; k < arr.size(); k++) {
        vector<int> testArr = arr;
        int result = findKthSmallest(testArr, k);
        int expected = arrCopy[k];
        
        cout << "k=" << k << ": 结果=" << result << ", 期望=" << expected;
        if (result == expected) {
            cout << " ✓" << endl;
        } else {
            cout << " ✗" << endl;
        }
    }
    
    // 测试一个更复杂的数组
    cout << "\n=== 测试更复杂数组 ===" << endl;
    vector<int> arr2 = {12, 3, 5, 7, 4, 19, 26, 1, 8};
    vector<int> arr2Copy = arr2;
    
    cout << "\n原始数组: ";
    printArray(arr2);
    
    sort(arr2Copy.begin(), arr2Copy.end());
    cout << "排序后数组: ";
    printArray(arr2Copy);
    
    // 只测试几个关键位置
    vector<int> testKs = {0, 2, 4, 6, 8};
    for (int k : testKs) {
        vector<int> testArr = arr2;
        int result = findKthSmallest(testArr, k);
        int expected = arr2Copy[k];
        
        cout << "k=" << k << ": 结果=" << result << ", 期望=" << expected;
        if (result == expected) {
            cout << " ✓" << endl;
        } else {
            cout << " ✗" << endl;
        }
    }
}

int main() {
    detailedTest();
    return 0;
}
