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

int main() {
    vector<int> arr = {1, 2, 3, 4, 5};
    
    cout << "Testing bisect function:" << endl;
    
    // Test case 1: target exists
    for (int i = 0; i < arr.size(); i++) {
        int result = bisect(arr, 0, arr.size()-1, arr[i]);
        cout << "Searching for " << arr[i] << ": result = " << result;
        if (result == i) {
            cout << " ✓" << endl;
        } else {
            cout << " ✗ (expected " << i << ")" << endl;
        }
    }
    
    // Test case 2: target doesn't exist
    vector<int> nonExistent = {0, 6, 10};
    for (int target : nonExistent) {
        int result = bisect(arr, 0, arr.size()-1, target);
        cout << "Searching for " << target << ": result = " << result;
        if (result >= 0 && result < arr.size() && arr[result] == target) {
            cout << " ✗ (found but shouldn't)" << endl;
        } else {
            cout << " (not found or insertion point)" << endl;
        }
    }
    
    // Test case 3: edge cases
    vector<int> empty = {};
    if (empty.size() > 0) {
        int result = bisect(empty, 0, empty.size()-1, 1);
        cout << "Empty array search: " << result << endl;
    }
    
    vector<int> single = {42};
    int result = bisect(single, 0, single.size()-1, 42);
    cout << "Single element array, searching for 42: " << result;
    if (result == 0) {
        cout << " ✓" << endl;
    } else {
        cout << " ✗" << endl;
    }
    
    return 0;
}
