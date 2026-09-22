/*
6-6 数组排序输出（函数模板）
分数 10
作者 何振峰
单位 福州大学
对于输入的每一批数，按从小到大排序后输出。

一行输入为一批数，第一个输入为数据类型（1表示整数，2表示字符型数，3表示有一位小数的浮点数，4表示字符串，0表示输入结束），第二个输入为该批数的数量size（0<size<=10），接下来为size个指定类型的数据。

输出将从小到大顺序输出数据。

函数接口定义：sort函数将接受size个数据，将它们从小到大排序后存在a指向的一段连续空间中。
template <class T>
void sort(T *a, int size)；
*/




#include <iostream>
#include <string>
using namespace std;

/* 请在这里填写答案 */
template <class T>
void sort(T *a, int size) {
      for (int i = 0; i < size; i++) {
          cin >> a[i];
      }

      for (int i = 0; i < size - 1; i++) {
          for (int j = 0; j < size - 1 - i; j++) {
              if (a[j] > a[j + 1]) {
                  T temp = a[j];
                  a[j] = a[j + 1];
                  a[j + 1] = temp;
              }
          }
      }
}
/*
  #include <algorithm>

  template <class T>
  void sort(T *a, int size) {
      for (int i = 0; i < size; i++) {
          cin >> a[i];
      }

      std::sort(a, a + size);
  }


*/



template <class T>
void display(T* a, int size){
    for(int i=0; i<size-1; i++) cout<<a[i]<<' ';
    cout<<a[size-1]<<endl;
}



int main() {
     const int SIZE=10;
     int a[SIZE];
     char b[SIZE];
     double c[SIZE];
     string d[SIZE];
     int ty, size;
     cin>>ty;
     while(ty>0){
         cin>>size;
         switch(ty){
             case 1:sort(a,size); display(a,size); break;
             case 2:sort(b,size); display(b,size); break;
             case 3:sort(c,size); display(c,size); break;
             case 4:sort(d,size); display(d,size); break;
         }
         cin>>ty;
     }
      return 0;
}
