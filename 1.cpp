#include <iostream>
#include <vector>

using namespace std;

namespace foo
{
int x;
int u;

}  // namespace foo

int main()
{
    foo::x = 2;
    int x = 1;
    cout << x << " " << foo::x << endl;
    int a[4] = {4 * 12};
    cout << a[0] << endl;
    cout << a[1] << a[3];
    return 0;
}