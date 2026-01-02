#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <set>
#include <<unordered_set>
using namespace std;



class Solution {
public:
    int repeatedNTimes(vector<int>& n) {
        int length = n.size();
        vector<int> a (10e4,0);
        for(int i=0;i<length;i++) 
        {
            a[n[i]]++;
            if(a[n[i]] >0) return n[i];
        }
    }
};

class Solution {
public:
    int repeatedNTimes(vector<int>& nums) {
        unordered_set<int> set;

        for (int n: nums) {
            if (set.contains(n)) {
                return n;
            }
            set.insert(n);
        }
        return 0;
    }
};