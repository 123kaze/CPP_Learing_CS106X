#include <iostream>
#include <algorithm>
#include <vector>
using namespace std;

vector<vector<int>> graph;
int n,k;
vector<int> next1;
vector<int> indegree;
// dfs(i) = max(dfs(i.child)) +1 
int dfs(int node){
    if(graph[node].size() == 0){
        return 1;
    }
    int maxn = 0;
    for(auto& x:graph[node]){
        int cur = dfs(x);
        if(cur > maxn){
            next1[node] = x;
            maxn = cur;
        }
        else if (cur == maxn and x<next1[node])
        {
            next1[node] = x;
        }      
    }
    return maxn+1;
}

int main(){
    cin >> n;
    indegree.assign(n+1,0);
    graph.assign(n+1,vector<int>());
    next1.resize(n+1,-1);
    for(int i =1;i<=n;i++){
        cin>>k;
        for(int j=0;j<k;j++){
            int q;
            cin >>q;
            graph[i].push_back(q);
            indegree[q]++;
        }
    }
    int root = 0;
    for(int i=1;i<=n;i++){
        if (indegree[i] == 0){
            root = i;
            break;
        }
    }
    int res=0;
    res = dfs(root);
    cout<<res;
    int cur = root;
    while(cur != -1){
        cout<<next1[cur];
        cur = next1[cur];
    }
}


