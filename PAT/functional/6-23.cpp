#include <string>
#include <iostream>
using namespace std;
// int num = 0;
// int sum = 0;
class Stud{
    public:
    int grade,id;
    static int sum,num;
    string name;
    Stud(int x,string y,int grade):id(x),name(y),grade(grade) {
        //1，Li，89
        // cout<<x<<", "<<name<<", "<<grade<<endl;
        num+=1;
        sum+=grade;
    }
    void disp(){
        cout<<id<<"，"<<name<<"，"<<grade<<endl;
    }
    static double avg(){
        return sum/num;
    }
};