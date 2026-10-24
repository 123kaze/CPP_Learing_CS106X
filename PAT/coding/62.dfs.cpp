#include <bits/stdc++.h>
using namespace std;
using ll = long long;
vector<vector<int>> g;
unordered_map<int,vector<int>> gg;
vector<int> res;
vector<bool> visited;

unordered_set<long long> bad;

int n;
bool dfs(int node,vector<int>& path) {
    if (path.size() == n){
        if (find(g[node].begin(), g[node].end(), 1)
        != g[node].end()){
            return true;
        }
        return false;
    }
    ll musk = 0;
    for (int i=1;i<=n;i++){
        if(visited[i]){
        musk = musk | 1LL<<(i-1);
    }}
    long long state = (musk << 5) | node;
    if (bad.count(state)) {
    return false;
    }

    for (auto child : g[node]){
        if (child == 0){
            continue;
        }
        if (visited[child]){
            continue;
        }
        visited[child] = true;
        path.push_back(child);
        bool res= dfs(child,path);
        if (res != false){
            return res;
        }
        visited[child] = false;
        path.pop_back();
    }
    bad.insert(state);
    return false;
}

int main(){
    cin>>n;
    g.assign(n+1,vector<int>(n+1,0));
    visited.assign(n+1,false);
    visited[1] = true;
    for(int i=1;i<=n;i++){
        for(int j=1;j<=n;j++){
            char s;
            cin>>s;
            if (s == 'W'){
                g[i][j] = j;
            }
            if (s == 'L'){
                g[j][i] = i;
            }
        }
    }
    vector<int>path;
    path.push_back(1);
    vector<int>*res = dfs(1,path);
    if (res==nullptr){
        cout<<"No Solution"<<endl;
    }
    else{
        for (auto x:*res){
            if(x == 1){
                cout<<x;
            }else{
            cout<<" "<<x;
        }}
        cout<<endl;
    }
}