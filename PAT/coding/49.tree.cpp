#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

class Node{
    public:
    int val;
    Node* left;
    Node* right;

    Node(int v):val(v){};
};
vector<int> poso,ino;
vector<int> res1;
vector<int> res2;

void dfs(Node* root,vector<int>& res,int depth,bool left){
    if (root == nullptr){
        return ;
    }
    if (depth == res.size()){
        res.push_back(root->val);
    }
    if (left){
        dfs(root->left,res,depth+1,true);
        dfs(root->right,res,depth+1,true);
    }else{
        dfs(root->right,res,depth+1,false);
        dfs(root->left,res,depth+1,false);
    }   
}

Node* build(int il, int ir, int pl, int pr){
    if (il>ir){
        return nullptr;
    }
    Node* root =  new Node(poso[pr]);
    int rootVal = poso[pr];

    int k =find(ino.begin(), ino.end(), rootVal) - ino.begin();
    int leftsize = k-il;

    root->left = build(il,k-1,pl,pl+leftsize-1);
    root->right = build(k+1,ir,pl+leftsize,pr-1);
    return root;
}



int main(){
    int n,i;
    cin >>n;
    ino.resize(n);
    poso.resize(n);

    for(i=0;i<n;i++){
        cin>>ino[i];
    }
    for(i=0;i<n;i++){
        cin>>poso[i];
    }
    Node* root = build(0,n-1,0,n-1);
    dfs(root,res1,0,true);
    dfs(root,res2,0,false);
    cout<<"R:";
    for(auto re:res2){
        if (re !=0) cout<<' '<<re;
    }
    cout<<endl;
    cout<<"L:";
    for(auto re:res1){
        if (re !=0) cout<<' '<<re;
    }
    return 0;
}