/*
定义一个CPU类，包含等级（Rank）、频率（frequency）、电压(voltage)等属性。其中，rank为枚举类型CPU__Rank,
定义为enum CPU_Rank{P1=1,P2,P3,P4,P5,P6,P7},frequency为单位是MHz的整型数，voltage为浮点型的电压值。
*/
/* 请在这里填写答案 */
#include <iostream>
using namespace std;

enum CPU_RANK{
    P1 = 1,
    P2 = 2,
    P3,
    P4,
    P5,
    P6,
    P7
};

class CPU{
    public:
    CPU_RANK Rank;
    int frequency;
    float voltage;
     CPU()
          : Rank(P1), frequency(0), voltage(0.0f) {
          cout << "create a CPU!" << endl;
      }
    CPU(CPU_RANK p,int i,float f):Rank(p),frequency(i),voltage(f){
        cout<<"create a CPU!"<<endl;
    }
    CPU(const CPU& other)
        : Rank(other.Rank), frequency(other.frequency), voltage(other.voltage){
        cout<<"copy create a CPU!"<<endl;
    }
    void showinfo(){
        cout<<"rank:"<<Rank<<endl;
        cout<<"frequency:"<<frequency<<endl;
        cout<<"voltage:"<<voltage<<endl;
    }
    ~CPU() {
      cout << "destruct a CPU!" << endl;
  }
};
int main()
{
    CPU a(P6,3,300); 
    
    cout<<"cpu a's parameter"<<endl;
    a.showinfo(); //显示性能参数

    CPU b; 
    cout<<"cpu b's parameter"<<endl;
    b.showinfo(); //显示性能参数

    CPU c(a); 
    cout<<"cpu c's parameter"<<endl;
    c.showinfo(); //显示性能参数
}
