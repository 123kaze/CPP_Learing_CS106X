#include <bits/stdc++.h>
using namespace std;

class CPoint {
    public:
    int x;
    int y;
    CPoint(int x,int y):x(x),y(y){}
};

class CLine {
    public:
    CPoint x;
    CPoint y;
    CLine(CPoint q,CPoint w):x(q),y(w){count+=1;}
    CLine(CLine &other):x(other.x),y(other.y){count+=1;}
    int GetLen(){
        return sqrt((x.x-y.x)*(x.x-y.x)+(x.y-y.y)*(x.y-y.y));
    }
    inline static int count=0;
    static int ShowCount(){
        return count;
    }
};