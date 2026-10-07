/*
7-64 至多删三个字符
分数 20
作者 曹鹏
单位 Google
给定一个全部由小写英文字母组成的字符串，允许你至多删掉其中 3 个字符，结果可能有多少种不同的字符串？

输入格式：
输入在一行中给出全部由小写英文字母组成的、长度在区间 [4, 10**6] 内的字符串。
ababcc
输出格式：
在一行中输出至多删掉其中 3 个字符后不同字符串的个数。
*/
#include <bits/stdc++.h>
using namespace std;

string s;
vector<vector<long long>> dp;
// vector<int> last;

int dfs(int i,int j){

}
/*
dfs(i,j) = dfs(i-1,j)+dfs(i-1,j-1) - dfs(k-1,j-(i-k))
*/


int main(){
    cin >> s;
    int last[26] = {0};
    int n = s.size();
    dp.assign(n+1,vector<long long>(4,0));
    dp[0][0] = 1;
    for(int i=1;i<=n;i++){
        int c = s[i-1] - 'a';
        int k = last[c];
        for(int j=0;j<4;j++){
            dp[i][j] = dp[i - 1][j];
            if (j>0){
                dp[i][j]+=dp[i-1][j-1];
            }
            if (k!=0){
                int d = i-k;
                if (j >= d){
                dp[i][j] -= dp[k-1][j-d];
            }
        }
        }   
        last[c] = i;
    }
    long long res = 0;
    for (int j=0;j<4;j++){
        res+=dp[n][j];
    }
    cout<<res;
    return 0;
}

