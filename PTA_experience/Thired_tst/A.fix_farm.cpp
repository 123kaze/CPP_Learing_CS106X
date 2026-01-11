#include <algorithm>
#include <cmath>
#include <iostream>
#include <queue>
#include <tuple>
#include <utility>
#include <vector>
using namespace std;

int getMin(priority_queue<int, vector<int>, greater<int>>& minheap)
{
    int min1 = minheap.top();
    minheap.pop();
    return min1;
}

int main()
{
    int n;
    cin >> n;
    priority_queue<int, vector<int>, greater<int>> minheap;
    for (int i = 0; i < n; i++)
    {
        int l;
        cin >> l;
        minheap.push(l);
    }

    int total = 0;
    while (minheap.size() > 1)
    {
        /* code */
        int min1 = getMin(minheap);
        int min2 = getMin(minheap);

        int sum = min1 + min2;
        total += sum;
        minheap.push(sum);
    }

    cout << total << endl;
    return 0;
}