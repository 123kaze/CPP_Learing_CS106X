#include <iostream>
#include <vector>
#include <string>

using namespace std;

namespace foo {
    int x;
    int u;
}

int nameDiamond(string s){
    int i=0,j=0,l=0;
    l = s.length();
    for(j=0;j<=l;j++){
    for(i=0;i<j;i++){
        if(i==j-1){
            cout<<s[i]<<endl;
        }
        else{
        cout<<s[i];
    }
    }
    }
    return 0;
}




int main(){
    string s = "Hi D00d!";
    
    char c1 = s[3];
    char c2 = s.at(3);
    //characters have ascii endcodings
    cout << (int)s[0] << endl; //72

    string s1 = "Mar";
    s1 += "ty"; //marty

    string s2 = "Cynthia";
    if (s1 > s2 &&s2 != "Joe"){ //逐字符比较，最多遇到末尾。ascii


    }

    s1.append(" Steppp"); //marty steppp
    s1.erase(3,2);// mar steppp              erase(start,length)
    s[6] = 'o'; //mar stopp

    //s.find(str) s.rfind(str)  first or last index where the strat of str appears in this string
    //s.insert(index,str )       add text into a string 
    //s.replace(index,len,str)   replaces len chars at given index with new text
    //s.substr(start,length) or (start)      slice it form start. if length omitted,grabs till end of string.

    string name = "Donald Knuth";
    if (name.find("Kun") != string::npos){ // npos 表示 not a position 不是一个有效的位置它是一个特殊的值，
                                            //通常定义为 size_t 类型的最大值（通常是 -1 或 18446744073709551615 对于 64 位系统）。
                                            // ：： 类似于访问类的静态成员
        name.erase(7,5); //"Donlad"
    }
    
    // s.endwith(str,suffix) s.startwith(str,prefix)    bool
    //intergerToString(int)    convert
    //to

    /*
    ====================================================
    string 常用方法总结：
    ====================================================
    
    1. 构造与赋值：
       - string() / string("text")          // 构造函数
       - string str = "text";               // 赋值
       - str = other_str;                   // 字符串赋值
       - str.assign("text")                 // 赋值方法
    
    2. 访问元素：
       - str[index]                         // 访问字符（不检查边界）
       - str.at(index)                      // 访问字符（检查边界，越界抛出异常）
       - str.front()                        // 第一个字符
       - str.back()                         // 最后一个字符
    
    3. 容量相关：
       - str.size() / str.length()          // 字符串长度
       - str.empty()                        // 是否为空
       - str.capacity()                     // 当前分配的存储容量
       - str.reserve(n)                     // 预留存储空间
       - str.shrink_to_fit()                // 减少容量以匹配大小
    
    4. 修改操作：
       - str += "text"                      // 追加字符串
       - str.append("text")                 // 追加字符串
       - str.push_back('c')                 // 追加单个字符
       - str.insert(pos, "text")            // 在指定位置插入
       - str.erase(pos, len)                // 删除从pos开始的len个字符
       - str.replace(pos, len, "text")      // 替换从pos开始的len个字符
       - str.clear()                        // 清空字符串
       - str.pop_back()                     // 删除最后一个字符
    
    5. 查找操作：
       - str.find("text")                   // 查找子串首次出现位置
       - str.rfind("text")                  // 查找子串最后一次出现位置
       - str.find_first_of("chars")         // 查找任何指定字符首次出现
       - str.find_last_of("chars")          // 查找任何指定字符最后一次出现
       - str.find_first_not_of("chars")     // 查找不在指定字符集中的字符首次出现
       - str.find_last_not_of("chars")      // 查找不在指定字符集中的字符最后一次出现
    
    6. 子串操作：
       - str.substr(pos, len)               // 提取子串
       - str.compare("text")                // 比较字符串
       - str.compare(pos, len, "text")      // 比较子串
    
    7. 输入输出：
       - getline(cin, str)                  // 从输入流读取一行
       - cin >> str                         // 从输入流读取单词
       - cout << str                        // 输出字符串
    
    8. C风格字符串转换：
       - str.c_str()                        // 返回C风格字符串（const char*）
       - str.data()                         // 返回字符数组（C++17起与c_str()相同）
       - str.copy(buffer, len, pos)         // 复制到字符数组
    
    9. 迭代器：
       - str.begin() / str.end()            // 正向迭代器
       - str.rbegin() / str.rend()          // 反向迭代器
       - str.cbegin() / str.cend()          // 常量正向迭代器
       - str.crbegin() / str.crend()        // 常量反向迭代器
    
    10. 数值转换：
        - to_string(number)                 // 数值转字符串（C++11）
        - stoi(str) / stol(str) / stoll(str) // 字符串转整数
        - stof(str) / stod(str) / stold(str) // 字符串转浮点数
    
    11. 其他操作：
        - str.swap(other_str)               // 交换两个字符串
        - str.resize(n, 'c')                // 调整大小，可选填充字符
        - str.max_size()                    // 最大可能长度
    
    注意：string::npos 是一个特殊值，表示"未找到"或"无效位置"，
          通常用于查找函数的返回值检查。
    */



    cin >> name;//"jhon D" 
    cout<<name<<endl; // jhon   用getline(cin,name)就没有这个影响
    nameDiamond(name);


    return 0;



}
