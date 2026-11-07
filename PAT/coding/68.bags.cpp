#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

vector<int> bags,values;
int n,capacity;

vector<vector<long long>> memo;

vector<long long> dp;

vector<vector<bool>> choose;


int main(){
    cin >> n>> capacity;
    bags.resize(n);
    values.resize(n);
    dp.assign(capacity+1,0);
    choose.assign(n+1,vector<bool>(capacity+1,false));
    for(int i=0;i<n;i++){
        cin>>bags[i];
    }
    for(int i=0;i<n;i++){
        cin>>values[i];
    }
    /*
    dp[j] = max(dp[j],dp[j-w[i]]+v[i]) for j in range(n,-1,-1)
    */
   for(int i=0;i<n;i++){
    for (int j=capacity;j>=bags[i];j--){
        if (dp[j]>dp[j-bags[i]]+values[i]){
        dp[j] = dp[j-bags[i]]+values[i];
        choose[i][j] == true;
    }}
   }
   cout<<dp[capacity];
   vector<int> x(n, 0);
   int j = capacity;
   for (int i = n - 1; i >= 0; i--) {
        if (choose[i][j]) {
            x[i] = 1;
            j -= bags[i];
        }
    }
    for (int i = 0; i < n; i++) {
        cout << x[i] << " ";
    }
}