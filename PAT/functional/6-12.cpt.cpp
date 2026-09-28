#include <iostream>
using namespace std;

enum CPU_RANK {
    P1 = 1,
    P2,
    P3,
    P4,
    P5,
    P6,
    P7
};

class CPU {
public:
    CPU_RANK Rank;
    double frequency;
    int voltage;

    CPU(int rank = 1, double f = 2.0, int v = 100)
        : Rank(static_cast<CPU_RANK>(rank)), frequency(f), voltage(v) {
        cout << "create a CPU!" << endl;
    }

    CPU(const CPU& other)
        : Rank(other.Rank), frequency(other.frequency), voltage(other.voltage) {
        cout << "create a CPU by copy!" << endl;
    }

    ~CPU() {
        // 按题目样例保留 desturct 的拼写
        cout << "desturct a CPU!" << endl;
    }

    void showinfo() {
        cout << "cpu parameter:" << endl;
        cout << "rank:" << Rank << endl;
        cout << "frequency:" << frequency << endl;
        cout << "voltage:" << voltage << endl;
    }
};

class RAM {
public:
    int volumn;

    RAM(int v = 1) : volumn(v) {
        cout << "create a RAM!" << endl;
    }

    RAM(const RAM& other) : volumn(other.volumn) {
        cout << "create a RAM by copy!" << endl;
    }

    ~RAM() {
        // 按题目样例保留 desturct 的拼写
        cout << "desturct a RAM!" << endl;
    }

    void showinfo() {
        cout << "ram parameter:" << endl;
        cout << "volumn:" << volumn << " GB" << endl;
    }
};

class CDROM {
public:
    int speed;

    CDROM(int s = 16) : speed(s) {
        cout << "create a CDROM!" << endl;
    }

    CDROM(const CDROM& other) : speed(other.speed) {
        cout << "create a CDROM by copy!" << endl;
    }

    ~CDROM() {
        cout << "destruct a CDROM!" << endl;
    }

    void showinfo() {
        cout << "cdrom parameter:" << endl;
        cout << "speed:" << speed << endl;
    }
};

class COMPUTER {
public:
    // 三个成员对象均为 public
    CPU cpu;
    RAM ram;
    CDROM cdrom;

    COMPUTER() : cpu(), ram(), cdrom() {
        cout << "no para to create a COMPUTER!" << endl;
    }

    COMPUTER(int rank, double frequency, int voltage, int volumn, int speed)
        : cpu(rank, frequency, voltage), ram(volumn), cdrom(speed) {
        cout << "create a COMPUTER with para!" << endl;
    }

    COMPUTER(const COMPUTER& other)
        : cpu(other.cpu), ram(other.ram), cdrom(other.cdrom) {
        cout << "create a COMPUTER by copy!" << endl;
    }

    ~COMPUTER() {
        cout << "destruct a COMPUTER!" << endl;
    }

    void showinfo() {
        cpu.showinfo();
        ram.showinfo();
        cdrom.showinfo();
    }

    void run() {}
    void stop() {}
};
