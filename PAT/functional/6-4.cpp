#include <iostream>
#include <string>
using namespace std;
class Coach{
    string name;
    int winRate;
public:
    Coach(string n, int wr){
        name=n; winRate=wr;
    }
    void show();
};
class Club{
    string name;
    Coach c;
    int year;
public:
    Club(string n1, int y, string n2, int wr);
    void show();
};
int main(){
    string n1, n2;
    int year, winRate;
    cin>>n1>>year>>n2>>winRate;
    Club c(n1,year, n2, winRate);
    c.show();
    return 0;
}

/* 请在这里填写答案 */

void Coach::show(){
    cout<<this->name<<" "<<this->winRate<<"%"<<endl;
}

void Club::show(){
    cout<<this->name<<" "<<this->year<<endl;
    this->c.show();
}

Club::Club(string n1, int y, string n2, int wr):name(n1),year(y),c(n2,wr){}