// #include <bits/stdc++.h>
#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;
using ll = long long;
int n;
ll a,b;
vector<long long>res; 
bool flag = false;
// dfs(i,num) = dfs(i+1,num*10+j) for j in range(10)
void dfs(int i, ll num)
{
    if (i == n) {
        if (num >= a && num <= b) {
        cout << num << endl;
        flag = true;
        }
        return;
    }

    for(int j=0;j<10;j++){
        if (i==0 && j==0){
            continue;
        }
        if (num*10+j <= b){
            ll x = num*10+j;
            if (x %(i+1) == 0){
                dfs(i+1,x);
            }
        }
    }
}

int main(){
    cin >> n>>a>>b;
    ll t = ll(a);
    res.reserve(n);
    dfs(0,0);
    if(!flag){
        cout<<"No Solution" << endl;
    }
    return 0;
}