/*
6-5 学生成绩的输入和输出（运算符重载）
分数 10
作者 何振峰
单位 福州大学
现在需要输入一组学生的姓名和成绩，然后输出这些学生的姓名和等级。

输入时，首先要输入学生数（正整数）N。接着输入N组学生成绩，每组成绩包括两项：第一项是学生姓名，第二项是学生的成绩（整数）。

输出时，依次输出各个学生的序号（从1开始顺序编号），学生姓名，成绩等级（不小于60为PASS，否则为FAIL）

函数接口定义：
面向Student类对象的流插入和流提取运算符
*/

#include <iostream>
#include <string>
using namespace std;

/* 请在这里填写答案 */
class Student {
    public:
    string name;
    int grade;

    friend istream& operator>> (istream& im,Student& st){
        im>>st.name>>st.grade;
        return im;
    }
    friend ostream& operator<< (ostream& om,Student& st){
        static int nums = 1;
        om << nums++<< ". " << st.name<< " ";
        if (st.grade >=60 ){
            om<<"PASS";
        }else{
            om<<"FAIL";
        }
        return om;
    }
};



int main(){
    int i, repeat;
    Student st;
    cin>>repeat;
    for(i=0;i<repeat;i++){
        cin>>st;
        cout<<st<<endl;
    }
    return 0;
}
