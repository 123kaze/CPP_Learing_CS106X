/*
著名的王牌间谍 007 需要执行一次任务，获取敌方的机密情报。已知情报藏在一个地下迷宫里，迷宫只有一个入口，里面有很多条通路，每条路通向一扇门。每一扇门背后或者是一个房间，或者又有很多条路，同样是每条路通向一扇门…… 他的手里有一张表格，是其他间谍帮他收集到的情报，他们记下了每扇门的编号，以及这扇门背后的每一条通路所到达的门的编号。007 发现不存在两条路通向同一扇门。

内线告诉他，情报就藏在迷宫的最深处。但是这个迷宫太大了，他需要你的帮助 —— 请编程帮他找出距离入口最远的那扇门。

输入格式：
输入首先在一行中给出正整数 N（<10 
5
 ），是门的数量。最后 N 行，第 i 行（1≤i≤N）按以下格式描述编号为 i 的那扇门背后能通向的门：

其中 K 是通道的数量，其后是每扇门的编号。

输出格式：
在一行中输出距离入口最远的那扇门的编号。题目保证这样的结果是唯一的。
*/
#include<bits/stdc++.h>
using namespace std;

int n;
vector<int> indegree;
vector<vector<int>> g;

// dfs(node) = dfs(node.child)+1
int dfs(int node){
    if (g[node].size() == 0){
        return 1;
    }
    int maxn = 0;
    for (auto child:g[node]){
        maxn = max(maxn,dfs(child));
    }
    return maxn+1;
}

int main(){
    cin>> n;
    indegree.assign(n+1,0);
    g.resize(n+1);

    for(int i=1;i<=n;i++){
        int k = 0;
        cin >> k;
        while(k--){
            int t = 0;
            cin>>t;
            indegree[t]++;
            g[i].push_back(t);
        }
    }
    int root = -1;
    for (int i =1;i<=n;i++){
        if (indegree[i] == 0){
            root = i;
            break;
        }
    }
    cout<<root;
    cout<<dfs(root);
}

