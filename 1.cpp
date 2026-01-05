#include <iostream>
#include <vector>

using namespace std;

namespace foo {
    int x;
    int u;
}

int main(){
    foo::x = 2;
    int x=1;
    cout << x << " "<< foo::x<<endl;
    return 0;

}