#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;
using ll = long long;
int n;
vector<vector<ll>> dp;
vector<int> m;
vector<vector<int>> path;

/* j>i
dp[i][i] = dp[j][i] == 0
dp[i][i+1] = m[i-1]*m[i]*m[i+1]
dp[i][j] = dp[i][k]+dp[k+1][j]+m[i-1]*m[k]*m[j] for j in range(i,j)
*/
ll dfs(int i,int j){
    ll& res = dp[i][j];
    if (res != 99999999) return res;
    if (i==j || j<i){
        res = 0;
        return res;
    }
    if (j==i+1){
        res = m[i-1]*m[i]*m[i+1];
        path[i][j] = i;
        return res;
    }
    int k = i;
    for(k;k<j;k++){
        ll q = dfs(i,k)+dfs(k+1,j)+m[i-1]*m[k]*m[j];
        if (q<res){
            res = q;
            path[i][j] = k;
        }
    }
    return res;
}
string build(int i,int j){
    if (i==j){
        return "M"+to_string(i);
    }
    int k = path[i][j];
    return "("+build(i,k)+"x"+build(k+1,j)+")";
}
int main(){
    cin>>n;
    m.resize(n+1);
    path.assign(n+1,vector<int>(n+1,-1));
    dp.assign(n+1,vector<ll>(n+1,99999999));
    for(int i=0;i<=n;i++){
        cin>>m[i];
    }
    ll res = dfs(1,n);
    cout<<res<<endl;
    string ts = build(1,n);
    cout<<ts<<endl;
}

