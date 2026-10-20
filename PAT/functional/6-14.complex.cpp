#include <bits/stdc++.h>
using namespace std;
class Complex {
    public:
    int x;
    int y;
    Complex(int x,int y):x(x),y(y){}
    Complex(){}
    void Display(){
        cout<<x;
        if (y<0){
            cout<<y<<"i"<<endl;
        }
        else{
            cout<<"+"<<y<<"i"<<endl;
        }
    }
};

Complex AddComplex(Complex c1,Complex c2){
    return Complex(c1.x+c2.x,c1.y+c2.y);
}