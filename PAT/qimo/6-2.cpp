#include<iostream>
#include <string>
using namespace std;
struct Node{
    string name;
    int start;
    int end;
    Node *next;
};
Node* add(Node *, Node *);
void display(Node *);
bool check(Node *head)
{
    if(head==NULL || head->next==NULL) return true;
    Node *p=head->next;
    if(head->start > p->start) return false;
    return check(p);
}
int main()
{
    Node *head=NULL, *p;
    int i, repeat;
    cin>>repeat;
    for(i=0;i<repeat;i++){
        p = new Node;
        cin>>p->name>>p->start>>p->end;
        p->next=NULL;
        head = add(head, p);
    }
    if(!check(head)) cout<<"ERROR"<<endl;
    display(head);
    return 0;
}

/* 请在这里填写答案 */

Node* add(Node * head, Node *node) {
    if (head == NULL || node->start < head-> start ){
        node->next = head;
        return node;
    }
    Node* p = head;
    while (p->next != NULL && p->next->start < node->start){
        p = p->next;
    }
    node->next = p->next;
    p->next = node;
    return head;
}

void display(Node * node){
    Node* p = node;

    while (p!=NULL){
        bool con = false;
        Node* q = node;
        while (q!= NULL){
             if (p != q &&
                  p->start < q->end &&
                  q->start < p->end) {
                  con = true;
                  break;
              }
            q=q->next;
        }
        if (con) {
            cout << '*';
        }
        cout << p->name << ' ' << p->start << ' ' << p->end << endl;
        p = p->next;
    }
}