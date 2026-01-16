#include <algorithm>
#include <cmath>
#include <iostream>
#include <queue>
#include <set>
#include <unordered_set>
#include <vector>
using namespace std;

int main()
{
    int n;
    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++)
    {
        cin >> a[i];
    }
    int l, h;
    cin >> l >> h;
    int res = 0;
    for (auto d : a)
    {
        if (d >= l && d <= h)
        {
            res += d;
        }
    }
    return res;
}