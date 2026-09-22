#include <iostream>
using namespace std;

class Tree {
public:
    Tree();//构造函数
    void grow(int years);//对数龄ages加上years
    void age();//显示数龄ages的值
private:
    int ages;//树龄
};

int main()
{
    Tree tree;
    int years;
    cin >> years;
    tree.grow(years);
    tree.age();

    return 0;
}

/* 你的代码将被嵌在这里 */
Tree::Tree():ages(1){}
void Tree::grow(int years){
    this->ages+=years;
}

void Tree::age(){
    cout<<this->ages<<endl;    
}