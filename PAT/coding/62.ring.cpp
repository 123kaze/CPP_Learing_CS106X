#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
using namespace std;
using ll = long long;

vector<vector<ll>> g;
unordered_map<int,vector<ll>>gg;
vector<bool> visited;
bool flag = false;
int n;
vector<int> res;
unordered_set<long long> memo;

bool dfs(int i,vector<int> &path){
    if (path.size()==n){
        if(find(g[i].begin(),g[i].end(),1) !=
        g[i].end()
        ){
        return true;
        }else{
                return false;
        }
    }
    ll musk = 0;
    for (int i=1;i<=n;i++){
        if(visited[i]){
        musk = musk | 1LL<<(i-1);
    }}
    ll state = (musk<<5) | i; 
    if (memo.count(state)) {
        return false;
    }
    for(auto& child : g[i]){
        if (child == 0){
            continue;
        }
        if(!visited[child]){
            path.push_back(child);
            visited[child] = true;
            bool res = dfs(child,path);
            if(res){
                return res;
            }
            visited[child] = false;
            path.pop_back();
        }
    }
    memo.insert(state);
    return false;
}

int main(){
    cin >> n;
    g.assign(n+1,vector<ll>(n+1,0));
    visited.assign(n+1,0);
    visited[1] = 1;
    for (int i=1;i<=n;i++){
        for(int j=1;j<=n;j++){
            char s;
            cin>>s;
            if (s=='L'){
                g[j][i] = i;
            }
            if (s=='W'){
                g[i][j] = j;
            }
        }
    }
    // for (auto x:g[3]){
    //         if(x == 1){
    //             cout<<x<<"   ";
    //         }else{
    //         cout<<" "<<x;
    //     }}
    vector<int> path;
    path.push_back(1);
    bool res = dfs(1,path);
    if(res){
        for (auto& x:path){
            if(x == 1){
                cout<<x;
            }else{
            cout<<" "<<x;
        }}
    }
    else{
        cout<<"No Solution";
    }
}
