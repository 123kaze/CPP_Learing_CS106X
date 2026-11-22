#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;
vector<int> inorder,postorder;
vector<int> res1,res2;
struct Node
{
    Node* left;
    Node* right;
    int val;
    Node(int a):val(a){}
};

Node* build(int il,int ir,int posti,int postr){
    // in : 前中后。 post:前后中
    int val = postorder[postr];
    Node* root = new Node(val);
    int position = find(inorder.begin(),inorder.end(),val) - inorder.begin();
    int leftsize = position-il;
    root->left = build(il,position-1,posti,posti+leftsize-1); // 因为是角标
    root->right = build(position+1,ir,posti+leftsize,postr-1);
    return root;
}

void dfs(Node* node,bool left,vector<int>& res,int depth){
    if (node == 0){
        return; 
    }
    if (depth == res.size()){
        res.push_back(node->val);
    }
    if (left){
        dfs(node->left,true,res,depth+1);
        dfs(node->right,true,res,depth+1);
    }
    else{
        dfs(node->right,false,res,depth+1);
        dfs(node->left,false,res,depth+1);
    }
}
