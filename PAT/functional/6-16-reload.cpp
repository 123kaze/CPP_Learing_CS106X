/*
运算符重载速记

a + b  会被编译器翻译成：
    a.operator+(b)      成员函数：左操作数是 *this，括号里只写右边
    operator+(a, b)     友元函数：两个操作数都写进参数

左边不是自己的类时只能用友元：2 * a（左边是 int）、cout << a（左边是 ostream）

返回类型：
    + - * /            返回值 Point          结果是新对象
    += -= 前置++ =     返回 Point&           return *this;
    后置++             返回值 Point          返回加之前的旧值
    == < >             返回 bool
    []                 返回 int& / T&        返回引用才能 a[0] = 100
    << >>              返回 ostream& / istream&   才能 cout << a << b

参数习惯写 const 类名&：引用不拷贝，const 能接临时对象（>> 的第二个参数不加 const）

易错：
    1. << 忘了 return os;
    2. << 的参数没加 const，cout << Point(1, 2) 编译不过
    3. 友元在类外定义时不加 类名::
    4. 后置 ++ 写 operator++(int)，int 不起名字
    5. 有指针成员才需要自己写 operator=：防自赋值，return *this;
    6. . :: ?: sizeof 不能重载；参数个数、优先级不能改
*/
#include <iostream>
using namespace std;

class Point {
    int x, y;
public:
    Point(int x = 0, int y = 0) : x(x), y(y) {}

    // 算术：返回新对象，不修改自己 → 末尾加 const
    Point operator+(const Point& o) const { return Point(x + o.x, y + o.y); }
    Point operator-() const { return Point(-x, -y); }       // 负号 -a，没有参数

    // 复合赋值：修改自己，返回自己的引用
    Point& operator+=(const Point& o) { x += o.x; y += o.y; return *this; }

    // 比较：sort / set / map 要用 <
    bool operator==(const Point& o) const { return x == o.x && y == o.y; }
    bool operator<(const Point& o) const { return x != o.x ? x < o.x : y < o.y; }

    // 自增：靠一个没用的 int 区分前置和后置
    Point& operator++() { ++x; ++y; return *this; }                  // ++a
    Point operator++(int) { Point t = *this; ++x; ++y; return t; }   // a++

    // 下标：返回引用才能被赋值
    int& operator[](int i) { return i == 0 ? x : y; }

    // 左边不是 Point → 友元
    friend Point operator*(int k, const Point& p) { return Point(k * p.x, k * p.y); }
    friend ostream& operator<<(ostream& os, const Point& p) {
        os << "(" << p.x << ", " << p.y << ")";
        return os;
    }
    friend istream& operator>>(istream& is, Point& p) {
        is >> p.x >> p.y;
        return is;
    }
};

/*
输入：7 8
输出：
(4, 6) (-1, -2) (2, 4) (7, 8)
(4, 6) 1 0
(4, 6) (5, 7) (6, 8)
(100, 8)
*/
int main() {
    Point a(1, 2), b(3, 4), c;
    cin >> c;
    cout << a + b << " " << -a << " " << 2 * a << " " << c << endl;
    a += b;
    cout << a << " " << (a == Point(4, 6)) << " " << (a < b) << endl;
    Point d = a++;
    cout << d << " " << a << " " << ++a << endl;
    a[0] = 100;
    cout << a << endl;
}
