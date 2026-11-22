#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;
using ll = long long ;

vector<vector<ll>> dp,path;
vector<int> m;
int n;

/*
dfs(i,j) = min(dfs(i,k)+dfs(k+1,j)+cost) cost = m[i-1]*m[k]*m[j]
for k in range(i,j)
dp[i][i] = 0 = dp[j][i]

*/
ll dfs(int i,int j){
    ll& res = dp[i][j];
    if (res != 9999999999){
        return res;
    }
    if (i==j){
        res = 0;
        return res;
    }
    if (i>j){
        res = 0;
        return res;
    }
    if (j == i+1){
        res = m[i-1]*m[i]*m[j];
        path[i][j] = i;
        return res;
    }
    for (int k =i;k<j;k++){
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
    return "("+build(i,k)+")x("+build(k+1,j)+")";
}


int main(){
    cin>>n;
    m.resize(n+1);
    for(int i=0;i<=n;i++){
        cin >>m[i];
    }
    path.assign(n+1,vector<ll>(n+1,0));
    dp.assign(n+1,vector<ll>(n+1,9999999999));
    ll res = 0;
    res = dfs(1,n);
    cout<<res<<endl;
    cout<<build(1,n)<<endl;
}
