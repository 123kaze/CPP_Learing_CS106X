#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

int percision(vector<int>& a,int left,int right)
{
    int mid = left + (right - left)/2;
    int pivoit = a[right];
    int i = left,j=right;

    while(i < j )
    {
        while(i<j && a[i]<=pivoit) i++;
        while(i<j && a[j]>=pivoit) j--;
        if(i<j) swap(a[i],a[j]);
    }
    swap(a[i],a[right]);
    return i;
}

void Quicksort(vector<int>& a,int left,int right)
{
    int i=left,j=right;
    if (left >= right) return;
    int piv_idx = percision(a,left,right);
    Quicksort(a,i,piv_idx -1);
    Quicksort(a,piv_idx+1,right);
}