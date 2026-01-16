#include <bits/stdc++.h>
using namespace std;

int left1(int i)
{
    return 2 * i + 1;
}

int right1(int i)
{
    return 2 * i + 2;
}

void judge(vector<int>& nums, int n, bool& minh, bool& maxh)
{
    for (int i = 0; i <= n / 2 - 1; i++)
    {
        int left = left1(i);
        int right = right1(i);

        if (left < n)
        {
            if (nums[i] < nums[left]) maxh = false;
            if (nums[i] > nums[left]) minh = false;
        }

        if (right < n)
        {
            if (nums[i] < nums[right]) maxh = false;
            if (nums[i] > nums[right]) minh = false;
        }
    }
}

int main()
{
    int n = 0;
    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++)
    {
        cin >> a[i];
    }

    bool minh = true;
    bool maxh = true;

    judge(a, n, minh, maxh);

    if (minh)
    {
        cout << "这是小根堆" << endl;
    }
    else if (maxh)
    {
        cout << "这是大根堆" << endl;
    }
    else
    {
        cout << "这不是堆" << endl;
    }

    return 0;
}