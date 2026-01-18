#include <iostream>
#include <vector>

using namespace std;

void sieveOfEratosthenes(int a, int b) {
    if (b < 2) return; // 2是最小的质数

    // 创建一个布尔数组，初始化为 true
    // isPrime[i] 表示数字 i 是否为质数
    vector<bool> isPrime(b + 1, true);
    
    // 0 和 1 不是质数
    isPrime[0] = isPrime[1] = false;

    // 埃氏筛核心逻辑
    for (int p = 2; p * p <= b; p++) {
        // 如果 isPrime[p] 没有被修改，那么它是一个质数
        if (isPrime[p]) {
            // 更新 p 的所有倍数，标记为非质数
            // 从 p*p 开始优化，因为比 p*p 小的倍数已经被之前的质数筛过了
            for (int i = p * p; i <= b; i += p)
                isPrime[i] = false;
        }
    }

    // 输出 [a, b] 范围内的质数
    for (int i = a; i <= b; i++) {
        if (isPrime[i]) {
            cout << i << endl;
        }
    }
}

int main() {
    int a, b;
    // 读取输入
    if (!(cin >> a >> b)) return 0;

    sieveOfEratosthenes(a, b);

    return 0;
}
