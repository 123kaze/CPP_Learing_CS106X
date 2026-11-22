#include<iostream>
#include <vector>
#include <algorithm>
using namespace std;
using ll = long long;

vector<int> wi,vi;
int n,w;
vector<ll> dp;
vector<vector<bool>> choose;
/*
dp[j] = max(dp[j],dp[j-w[i]]+v[i]) 
*/
int main(){
    cin>>n>>w;
    wi.resize(n+1);
    vi.resize(n+1);
    dp.assign(w+1,0);
    choose.assign(n+1,vector<bool>(w+1,0));
    dp[0] = 0;
    for(int i=0;i<n;i++){
        cin>>wi[i];
    }
    for(int i=0;i<n;i++){
        cin>>vi[i];
    }
    for (int i =0;i<n;i++){
        for (int j=w;j>=wi[i];j--){
            if (dp[j]<dp[j-wi[i]]+vi[i]){
                choose[i][j] = 1;
                dp[j] = dp[j-wi[i]]+vi[i];
            }
        }
    }
    cout<<dp[w]<<endl;
    vector<int> res(n,0);
    int j = w;
    for(int i=n-1;i>=0;i--){
        if (choose[i][j] == 1){
            j -= wi[i];
            res[i] = 1;
        }
    }
    for(auto & j:res){
        cout << j <<" ";
    }

}