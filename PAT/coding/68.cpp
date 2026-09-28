#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;
vector<int> bags,values;
int n,capacity;
/*
dfs(i,space) = max(dfs(i-1,space),dfs(i-1,space-bag[i]) if space > bag[i])
*/
vector<vector<long long>> memo;

long long dfs(int i ,int space){

    if (i<0){
        return 0;
    }
    long long& result = memo[i][space];
    if (result != -1) {
        return result;
    }
    if (space < bags[i]){
        result = dfs(i-1,space);
        return result;
    }
    result = max(dfs(i-1,space),dfs(i-1,space-bags[i])+values[i]);
    return result;
}

int main(){

    cin >> n>> capacity;
    bags.resize(n);
    values.resize(n);
    for(int i=0;i<n;i++){
        cin>>bags[i];
    }
    for(int i=0;i<n;i++){
        cin>>values[i];
    }
    memo.assign(n,vector<long long>(capacity+1,-1));
    const long long best_value = dfs(n - 1, capacity);

    vector<bool> selected(n,false);
    int space = capacity;

    for(int i=n-1;i>=0;--i){
        if (space >= bags[i] && values[i]+ dfs(i - 1, space - bags[i]) == dfs(i, space)){
            space-=bags[i];
            selected[i] = true;
        }
    }
    cout<<best_value<<endl;
    for(int i = 0;i<n;i++){
        if (selected[i]){
            cout<<1<<' ';
        }else{
            cout<<0<<' ';
        }
    }
    return 0;
}