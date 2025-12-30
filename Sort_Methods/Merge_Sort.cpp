#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

void merge(vector<int>& a,int left,int mid,int right)
{
    // int mid = left + (right - left)/2;
    int i = left,j = mid +1,k=0;  // temp index K

    vector<int> tmp(right - left +1);

    while(i <= mid&& j<= right) // 是《=
    {
        if(a[i]<=a[j]) tmp[k++] = a[i++];
        else  tmp[k++] = a[j++];
    }

    while(i<=mid) tmp[k++] = a[i++];
    while(j<=right) tmp[k++] = a[j++];

    for(int p=0;p<tmp.size();p++)
    {
        a[left+p] = tmp[p];
    }
}


void Mergesort(vector<int>& a,int left,int right)
{
    if (left >= right) return; //这里是大于等于》=
    int mid = left +(right-left)/2;
    Mergesort(a,left,mid);
    Mergesort(a,mid+1,right);
    merge(a,left,mid,right);
}