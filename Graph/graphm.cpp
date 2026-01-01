#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>
#include "grapgh1.h"
using namespace std;

class Graphm:public Graph
{
private:
    int numVertex,numEdge; //储存边和节点
    int **matrix; //printer to adj martrix
    int *mark;  //printer to mark array
public:
    Graphm(int numVert)  //构造函数
    { Init(numVert);}
    
};