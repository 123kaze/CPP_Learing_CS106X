#include <iostream>
using namespace std;

class parent {
    private:
    int weekday;
    int time;

    public:
    parent(int weekday, int time) {
        this->weekday = weekday;
        this->time = time;
    }
    ~parent() {
        cout << "Destructor called for parent class" << endl;
    }
    virtual int fee()=0;
};

class son:public parent {

    public:
    int rrr;

    son(int w, int t):parent(w, t) {
        rrr=0;
    }

    int fee() {
        return 100;
    }
};

int main() {
parent *p;
p = new son(1, 2);
cout << p->fee() << endl;
}