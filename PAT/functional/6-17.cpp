class Car{
    public:
    int m_nWheels = 0;

    void disp_welcomemsg(){
        cout << "Welcome to the car world!"<<endl;
    }
    void set_wheels(int n){
        m_nWheels = n;
    }
    int get_wheels(){
        return m_nWheels;
    }
};