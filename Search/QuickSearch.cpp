#include "../Treenode.h"
#include <iostream>
#include <vector>
#include <queue>
#include "../Sort_Methods/Quick.h"
using namespace std;

int quickSeclect(vector<int> a,int l ,int h,int k)
{
    int pivot = l;
    //use quick sort's ideas
    //put nums that <= pivot to the left
    for (int i=l;i<h;i++)
    {
        if(a[i]<=a[h])
    {
        swap(a[pivot++],a[i]);
    }
    swap(a[h],a[pivot]);
    }

}


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