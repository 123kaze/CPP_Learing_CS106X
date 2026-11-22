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
#include<iostream>
#include<vector>
#include<algorithm>
using namespace std;
using ll = long long;
/*
dp[i][j] = dp[i-1][j-1]+dp[i-1][j] - dp[last[val]][j-(i-last[val])] 1-based
dp[last[val]][j-(i-last[val])] == repeat[val][j-(i-last[val])]
*/
vector<ll> dp,dp1;
vector<vector<ll>> repeat;
int n;
string s;

/*
1.dp初始化 dp[0] =1
2.数组初始化
3.数组大小
*/

int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);
    cin>>s;
    n = s.size();
    dp.assign(4,0);
    dp[0]= 1;
    vector<int> last(26,0);
    vector<vector<ll>> repeat(26,vector<ll>(4,0));
    for(int i=1;i<=n;i++){
        int c = s[i-1] - 'a';
        int las = last[c];
        dp1.assign(4,0);
        for(int j=0;j<4;j++){
            dp1[j] = dp[j];
            if (j>0){
                dp1[j]+=dp[j-1];
            }
            if (las>0){
                if (j-(i-las)>=0){
                    dp1[j]-=repeat[c][j-(i-las)];
                }
            }
        }
        repeat[c] = dp;
        dp = dp1;
        last[c] = i;
    }
    ll res = 0;
    for (int j=0;j<4;j++)
    {
        res+=dp[j];
    }
    cout<<res;
    return 0;
}