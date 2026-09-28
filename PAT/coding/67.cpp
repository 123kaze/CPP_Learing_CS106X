#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int n;
vector<int> m;
vector<vector<int>> p;
vector<vector<long long>> dp;
// rcd
/*
    dp[i][i] = 0
    dp[i][i+1] = m[i-1]*m[i]*m[i+1]
    dp[i][j] = dp[i][k]+dp[k+1][j] + m[i-1]*m[k]*m[j]
*/
long long dfs(int i,int j){
    long long &res = dp[i][j];
    if (res != 999999999){
        return res;
    }
    if(i == j || i>j){
        res = 0;
        return res;
    }
    if (i== j-1){
        res = m[i-1]*m[i]*m[i+1];
        p[i][j] = i;
        return res;
    }
    int k=i;
    for (k;k<j;k++){
        long long q = dfs(i,k)+dfs(k+1,j)+m[i-1]*m[k]*m[j];
        if (res>(q)){
            res = q;
            p[i][j] = k;
        }
    }
    return res;
}
string build(int i, int j) {
    if (i == j) {
        return "M" + to_string(i);
    }

    int k = p[i][j];

    return "(" + build(i, k) + ")x(" + build(k + 1, j) + ")";
}

int main(){
    cin >> n;
    m.resize(n+1);
    for(int i=0;i<=n;i++){
        cin>>m[i];
    }
    /*
    dp[i][i] = 0
    dp[i][i+1] = m[i-1]*m[i]*m[i+1]
    dp[i][j] = dp[i][k]+dp[k+1][j] + m[i-1]*m[k]*m[j]
    */
   dp.assign(n+1,vector<long long>(n+1,999999999));
   p.assign(n + 1, vector<int>(n + 1, 0));
   long long ans = dfs(1,n);
   cout << build(1,n)<<endl;
   cout << ans <<endl;
//    cout << build(1,n)<<endl;
}
