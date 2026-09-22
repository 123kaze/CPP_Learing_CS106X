class Student {
    public:
        string num;
        string name;
        // zongchengji
        static int twosum;

    void output() const {
        cout << num << " " << name << endl;
    }
    Student(const string&id,const string &nm):num(id),name(nm){}
    virtual void display(){};
    virtual ~Student(){}
};

int Student::twosum = -1;

class GroupA:public Student {
    public:
    int sum;
    GroupA(const string& id,const string& nm,int s1,int s2):
    Student(id,nm),sum(s1+s2) {
        if (twosum < sum){
            twosum = sum;
        }
    }
    void display() {
        if (twosum == sum){
            output();
        }
    }
};

class GroupB:public Student {
    public:
    int sum;
    char grade;

    GroupB(const string& id,const string& nm,int s1,int s2,char g):
    Student(id,nm),sum(s1+s2),grade(g){
       if (twosum < sum){
            twosum = sum;
        }
    }
    void display() {
        // 第一名
        bool cons1 = (twosum == sum);
        bool cons3 = (sum*10>=twosum*7)&&(grade == 'A');
        if (cons1 || cons3){
            output();
        }
    }
    
};

class GroupC:public Student {
    public :
    int fivesum;
    GroupC(const string&id,const string& nm,int s1,int s2,int s3,int s4,
          int s5):Student(id,nm),fivesum(s1+s2+s3+s4+s5){
            
          }
    void display() {
        if (twosum >= 0 && 4 * fivesum >= 9 * twosum) {
              output();
          }
    }
};

