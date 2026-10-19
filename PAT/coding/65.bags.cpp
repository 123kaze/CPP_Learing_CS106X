#include <algorithm>
#include <iostream>
#include <numeric>
#include <vector>

using namespace std;
int n,m;
vector<int> w;
vector<int> v;
vector<int> dp;
int main() {
    cin>>n>>m;
    w.resize(n);
    v.resize(n);
    dp.assign(m+1,0);
    dp[0] = 0;
    for(int i=0;i<n;i++){
        cin>>w[i];
    }
    int sumV = 0;
    for(int i=0;i<n;i++){
        cin>>v[i];
        sumV+=v[i];
    }
    // dp[space] = max(dp[space - w[j]]+v[j],dp[j]) for j in range(space,m+1)
    for(int i=0;i<n;i++){
        for(int j=m;j>=w[i];j--){
            dp[j] = max(dp[j],dp[j-w[i]]+v[i]);
        }
    }
    
}
