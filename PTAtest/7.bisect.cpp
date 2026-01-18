#include <algorithm>
#include <iostream>
#include <vector>
using namespace std;
typedef long long ll;
const int MAXN = 100005;
int limit[MAXN];
int G[MAXN];
int tree[MAXN * 4];

void build(int node, int start, int end)
{
    if (start == end)
    {
        tree[node] = G[start];
        return;
    }
    int mid = (start + end) / 2;
    build(2 * node, start, mid);
    build(2 * node + 1, mid + 1, end);
    tree[node] = max(tree[2 * node], tree[2 * node + 1]);
}
int query(int node, int start, int end, int L, int R, int val)
{
    if (tree[node] < val || start > R || end < L) return -1;
    if (start == end) return start;

    int mid = (start + end) / 2;
    int res = query(2 * node + 1, mid + 1, end, L, R, val);
    if (res == -1)
    {
        res = query(2 * node, start, mid, L, R, val);
    }
    return res;
}

int main()
{
    int N;
    ll S;
    cin >> N >> S;
    vector<ll> A(N + 1);
    for (int i = 1; i <= N; i++) cin >> A[i];
    int r = 0;
    ll current_sum = 0;
    for (int l = 1; l <= N; l++)
    {
        while (r + 1 <= N && current_sum + A[r + 1] <= S)
        {
            r++;
            current_sum += A[r];
        }
        limit[l] = r - l + 1;
        G[l] = limit[l] - l;
        current_sum -= A[l];
    }
    build(1, 1, N);
    for (int i = 1; i <= N; i++)
    {
        if (limit[i] == 0)
        {
            cout << 0 << "\n";
            continue;
        }
        int L = i + 1, R = min(N, i + limit[i]);
        int j = query(1, 1, N, L, R, -i);

        if (j != -1)
            cout << 2 * (j - i) << "\n";
        else
            cout << 0 << "\n";
    }

    return 0;
}