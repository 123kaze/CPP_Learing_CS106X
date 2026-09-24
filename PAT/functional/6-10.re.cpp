#include <iostream>
#include <string>
using namespace std;
const int K=2;
const int N=20;
class Student{
  string name;
  Student *welcome[K];
  Student *pair;
  public:
      void init(string &name, Student *a, Student *b) {
        this->name=name; 
        welcome[0]=a;
        welcome[1]=b;
        pair=NULL;
      }
     void printPair();
     void addPair();        
};

/* 请在这里填写答案 */
void Student::addPair(){
    if (this->pair != NULL){
        return ;
    }
    for (int i = 0; i < 2; i++) {
        Student*fe = this->welcome[i];
        if (fe->pair != NULL) {
            continue;
        }
        bool welcomeMe =
            (fe->welcome[0] == this || fe->welcome[1] == this);
        
        bool bothPaired =
            (fe->welcome[0]->pair != NULL && fe->welcome[1]->pair != NULL);
        if (welcomeMe || bothPaired) {
            pair = fe;
            fe->pair = this;
            return; 
        }
    }
}

void Student::printPair(){
    pair != NULL
          ? static_cast<void>(cout << name << ":" << pair->name << endl)
          : static_cast<void>(0);
}

int main(){
    Student male[N], female[N];
    int m, f, i, j, a, b;
    string name;
    cin>>m;
    for(i=0;i<m;i++){
      cin>>name>>a>>b;
      male[i].init(name, &female[a], &female[b]);
    }
    cin>>f;
    for(i=0;i<f;i++){
      cin>>name>>a>>b;
      female[i].init(name, &male[a], &male[b]);
    }
    for(i=0;i<m;i++) male[i].addPair();
    for(i=0;i<f;i++) female[i].addPair();
    for(i=0;i<m;i++) male[i].printPair();
    return 0;
}

