// 拼题 A 的教超搞打卡活动，指定了 N 张打卡卷。第 i 张打卡卷需要 m_i 分钟做完，
// 完成后可获得 c_i 枚奖励的金币。活动规定每张打卡卷最多只能做一次，并且不允许提前交卷。
// 活动总时长为 M 分钟。请你算出最多可以赢得多少枚金币？

// 输入格式：
// 输入首先在第一行中给出两个正整数 N（≤ 10^3）和 M（≤ 365 × 24 × 60），
// 分别对应打卡卷的数量和以“分钟”为单位的活动总时长（不超过一年）。
// 随后一行给出 N 张打卡卷要花费的时间 m_i（≤ 600），最后一行给出对应的
// 奖励金币数量 c_i（≤ 30）。上述均为正整数，一行内的数字以空格分隔。

// 输出格式：
// 在一行中输出最多可以赢得的金币数量。
#include <bits/stdc++.h>
using namespace std;

int n,m;
vector<int> w;
vector<int> v;
vector<int> dp;

int main(){
    cin>>n>>m;
    w.resize(n);
    v.resize(n);
    // dp.assign(m+1,0);
    for(int i=0;i<n;i++){
        cin>>w[i];
    }
    int sumV = 0;
    for(int i=0;i<n;i++){
        cin>>v[i];
        sumV+=v[i];
    }
    dp.assign(sumV+1,99999999);
    dp[0] = 0;
    for(int i=0;i<n;i++){
        for(int j=sumV;j>=v[i];j--){
            dp[j] = min(dp[j-v[i]]+w[i],dp[j]);
        }
    }
    for (int j = sumV; j >= 0; j--) {
    if (dp[j] <= m) {
        cout << j << '\n';
        break;
    }
}
}