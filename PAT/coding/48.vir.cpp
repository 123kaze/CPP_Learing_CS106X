#include <bits/stdc++.h>
using namespace std;


int k;
vector<int> indegree;
vector<vector<int>> graph;
vector<int> nextNode;

// dfs(node) = 1+dfs(node.child)
int dfs(int node){
    if (graph[node].size() == 0){
        return 1;
    }
    int maxn = 0;
    for(auto child:graph[node]){
        int len = dfs(child);
        if (len< maxn){ // 这是>不是《
            maxn = len;
            nextNode[node] ;// = child;
        }
        else if (len == maxn && child < nextNode[node]) {
            nextNode[node] = child;
        }
    }
    return maxn+1;
}

int main(){
    cin>>k;
    int n = k;
    indegree.assign(n,0);
    graph.resize(n);
    nextNode.assign(n, -1);
    for (int i=0;i<k;i++){
        int t = 0;
        cin >> t;
        while (t--)
        {
            int x;
            cin >> x;
            graph[i].push_back(x);
            indegree[x]++;
        }
    }
    int root = -1;
    for(int i = 0;i<n;i++){
        if (indegree[i] == 0){
            root = i;
            break;
        }
    }

    cout<<dfs(root)<<endl;
    
    while(root != -1){
        cout<<root;
        root = nextNode[root];
        if (root != -1){
            cout<<" ";
        }
    }
}