#include <algorithm>
#include <cmath>
#include <iostream>
#include <queue>
#include <set>
#include <stack>
#include <string>
#include <unordered_set>
#include <vector>
using namespace std;

int main()
{
    string inp, outp;
    cin >> inp >> outp;

    stack<char> s;
    string ops = "";
    int inidx = 0, oidx = 0;
    int n = inp.size();

    while (oidx < outp.size())
    {
        if (!s.empty() && s.top() == outp[oidx])
        {
            s.pop();
            ops += 'O';
            oidx++;
        }
        else if (inidx < n)
        {
            s.push(inp[inidx]);
            inidx++;
            ops += 'P';
        }
        else
        {
            break;
        }
    }

    if (oidx == inidx)
    {
        cout << "right" << endl;
        cout << ops << endl;
    }
    else
    {
        cout << "wrong" << endl;
        vector<char> remain;
        while (!s.empty())
        {
            remain.push_back(s.top());
            s.pop();
        }
        int m = remain.size() - 1;
        for (; m >= 0; m--)
        {
            cout << remain[m];
        }
        cout << endl;
    }
}