#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

int bisect(vector<int>& a,int l,int h,int target)
{
    // 标准二分查找实现
    while(l <= h)
    {
        int mid = l + (h - l)/2;
        if(a[mid] < target) {
            l = mid + 1;
        } else if(a[mid] > target) {
            h = mid - 1;
        } else {
            return mid;  // 找到目标
        }
    }
    return -1;  // 未找到
}
