#include <iostream>
#include <vector>
#include <unordered_map>

using namespace std;

/*
分书问题。
给定 ``n`` 个人对 ``m`` 本书的喜好关系（``n <= m <= 8``），为每个人
分配一本其喜欢的书。每人恰好分到一本书，每本书至多分给一个人；列出所有
满足条件的分配方案。
输入：
    第一行包含正整数 ``n`` 和 ``m``，分别表示人数和书的数量。
    随后 ``n`` 行各包含 ``m`` 个 0 或 1：第 ``i`` 行第 ``j`` 列为 1 表示
    第 ``i`` 个人喜欢第 ``j`` 本书，0 表示不喜欢。
输出：
    按字典序升序输出所有方案 ``(s1, ..., sn)``，其中 ``si`` 表示第 ``i``
    个人分到的书号。

字典序：
    对方案 ``a`` 和 ``b``，若存在 ``k``，使得所有 ``i < k`` 均有
    ``a[i] == b[i]``，且 ``a[k] < b[k]``，则 ``a < b``。
*/

vector<int> path;
vector<bool> visited;
vector<vector<int>> needs;
int n,m;
void dfs(int i,vector<int>& path){
    if (i==n){
        cout<<'(';
        for (int j=0;j<n;j++){
            if(j>0){
                // 必须使用字符串；单引号的 ', ' 会被 C++ 当作多字符整数字面量。
                cout << ", ";
            }
            cout << path[j];
        }
        cout<<')'<<endl;
        // 输出完整方案后必须返回，否则会访问不存在的 needs[n][book]。
        return;
    }

    // j 是书的下标，范围应为 [0, m)，不能写成 [0, n)。
    for(int j=0;j<m;j++){
        if (needs[i][j] == 1 && !visited[j]){
            path.push_back(j+1);
            visited[j] = true;
            dfs(i+1,path);
            path.pop_back();
            visited[j] = false;
        }
    }
}


int main(){
    
    cin >> n >> m;
    
    // 每个人只会向 path 添加一本书；reserve 只预留空间，不会添加元素。
    path.reserve(n);
    // needs[person][book]：n 行分别对应人，m 列分别对应书。
    needs.assign(n,vector<int>(m));
    for(int i=0;i<n;i++){
        for (int j=0;j<m;j++){
            int p = 0;
            cin >> p;
            // 不能交换两层循环的上限，否则可能写入不存在的 needs[m][...]。
            needs[i][j] = p;
        }
    }
    visited.assign(m,false);
    dfs(0,path);
    
}
