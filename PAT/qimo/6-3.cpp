#include <iostream>
#include <string>
using namespace std;
class Student{
    int rank;
    string name;
    public:
        int getRank(){return rank;    }
        Student(string name, int rank):name(name), rank(rank){    }
        ~Student(){ cout<<name<<endl;}
};
int main(){
    int rank, count=0;
    const int SIZE=100;
    Student *pS[SIZE];
    string name;
    cin>>rank;
    while(count<SIZE && rank>0){
        cin>>name;
        pS[count++]= new Student(name, rank);
        cin>>rank;
    }

/* 请在这里填写答案 */
    for(int i=0;i<count;i++){
        for(int j=0;j<count-1;j++){
            if (pS[j]->getRank()>pS[j+1]->getRank()){
                Student *tmp = pS[j];
                pS[j] = pS[j+1];
                pS[j+1] = tmp;
            }
        }
    }

    for (int i=0;i<count;i++){
        pS[i]->~Student();
    }
    return 0;
}