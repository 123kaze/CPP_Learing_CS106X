#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

//寻找第k小的元素
double findKth(vector<int>& nums1,int l1,int h1,vector<int>& nums2, int l2,int h2,int k)
{
    int m = h1 - l1 -1;
    int n = h2 - l2 -1;

    if (m>n){
        return findKth(nums2,l2,h2,nums1,l1,h2,k);
    }

    if(m==0)
    {
        return nums2[l2+k-1];
    }

    if(k==1)
    {
        return min(nums1[l1],nums2[l2]);
    }

    int na = min(k/2,m);
    int nb = k - na;
    int va = nums1[l1 + na -1];
    int vb = nums2[l1 + nb -1];

    if(va == vb)
    {
        return va;
    }
    else if (va<vb){
        return findKth(nums1,l1+na,h1,nums2,l2,l2+nb-1,k-na);
    }
    else
    {
        return findKth(nums1,l1+na,l1+na-1,nums2,l2+nb,h2,k-nb);
    }
}



// 方案1：使用vector，可以获取长度
double findMedianSortedArrays(vector<int>& nums1, vector<int>& nums2) {
    int m = nums1.size();  // 正确获取长度
    int n = nums2.size();  // 正确获取长度
    
    int k = (m+n)/2;

    if((m+n)%2==1){
        return findKth(nums1,0,m-1,nums2,0,n-1,k+1);
    }
    else
    {
        return (findKth(nums1,0,m-1,nums2,0,n-1,k)+findKth(nums1,0,m-1,nums2,0,n-1,k+1))/2.0;
    }
}

/* // 方案2：如果必须使用原生数组，需要传递长度参数
double findMedianSortedArrays(int nums1[], int m, int nums2[], int n) {
    // m 和 n 分别是两个数组的长度
    // 这里可以继续实现算法
    // 暂时返回0.0作为占位符
    return 0.0;
}

// 方案3：使用模板获取数组长度（仅适用于编译时已知大小的数组）
template <size_t M, size_t N>
double findMedianSortedArrays(int (&nums1)[M], int (&nums2)[N]) {
    // M 和 N 是编译时已知的数组大小
    // 这里可以继续实现算法
    // 暂时返回0.0作为占位符
    return 0.0;
} */

int main() {
    // 测试示例
    vector<int> nums1 = {1, 3};
    vector<int> nums2 = {2};
    
    double result = findMedianSortedArrays(nums1, nums2);
    cout << "中位数: " << result << endl;
    
    return 0;
}
