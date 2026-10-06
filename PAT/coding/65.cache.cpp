#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;
int m,n;
vector<int> w,v;
vector<vector<long long>> cache;
long long dfs(int i,int space){
    if (i<0){
        return 0;
    }
    long long &res = cache[i][space];
    if (cache[i][space] != -1){
        return res;
    }
    if (space < w[i]){
        res = dfs(i-1,space);
        return res;
    }
    res = max(dfs(i-1,space),dfs(i-1,space-w[i])+v[i]);
    return res;
}

int main(){
    cin >> n>>m;
    w.resize(n);
    v.assign(n,0);
    cache.assign(n+1,vector<long long>(m+1,-1));
    for(int i=0;i<n;i++){
        cin>>w[i];
    }
    for(int i=0;i<n;i++){
        cin>>v[i];
    }
    cout<<dfs(n-1,m);
}