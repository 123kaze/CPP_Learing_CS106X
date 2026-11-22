#include <bits/stdc++.h>
using namespace s
using ll = long long;
bool flag;
int n;
vector<ll> res;
ll a,b;
// dfs(i,0) = 
void dfs(int i,ll num){
    if(i==n){
        if (num>=a and num<=b ){
            cout<<num<<endl;
            flag = true;
        }
        return;
    }
    for(int j=0;j<10;j++){
        if (i==0 and j==0){
            continue;
        }
        if (num*10+j<=b){
            ll x = num*10+j;
            if (x%(i+1) == 0){
                dfs(i+1,x);
            }
        }
    }
}

int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);
    cin>>n>>a>>b;
    dfs(0,0);
    if(!flag){
        cout<<"No Solution" << endl;
    }
    return 0;
}


