#include <iostream>
using namespace std;

class Rectangle {
public:
    void setLength(int l);//设置矩形的长度
    void setWidth(int w); //设置矩形的宽度
    int getArea();        //计算并返回矩形的面积
private:
    int length, width;    //矩形的长度和宽度    
};

int main()
{
    Rectangle r;
    int len, w;
    cin >> len >> w;
    r.setLength(len);
    r.setWidth(w);
    cout << r.getArea() << "\n";

    return 0;
}

/* 你的代码将嵌在这里 */

void Rectangle::setLength(int l){
    this->length = l;
}
void Rectangle::setWidth(int w){
    this->width = w;
}
int Rectangle::getArea(){
    return this->length*this->width;
}