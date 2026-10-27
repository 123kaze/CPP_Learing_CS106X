#include <bits/stdc++.h>

template<class T>
class Vector {
    public:
    vector<T> a;
    
    int add(const T num){
        a.push_back(num);
        return a.size()-1;
    }
    int get_size(){
        return a.size();
    }
    T& operator[](int index) { return a[index]; }
    void remove(int m){
        a.erase(a.begin()+m);
    }
};