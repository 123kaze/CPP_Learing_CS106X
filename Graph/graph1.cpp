#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>
#include "grapgh1.h"
using namespace std;

class Graph {
private:
    void operator = (const Graph&) {} // protect assignment
    Graph (const Graph&) {} // protect copy constructor

public:
    Graph ( ) {} //Default 
    virtual ~Graph() {} // destructor

    // Initalize a graph 
    virtual void Init(int n) =0;

    // the number of vertices and edges
    virtual int n() = 0;
    virtual int e() = 0;

    //return v's first neighbor
    virtual int first(int v) = 0;
    // return v's next neighbor
    virtual int next(int v,int w) = 0;

    //set the weight for an egdeS
    //i,j:vertices
    //wgt: Edge weight
    virtual void setEdge(int v1,int v2,int wig) = 0;

    //Delete egde
    // i,j : the vertices
    virtual void delEdge(int v1,int v2) = 0;
    //Determine if an edge is in a graph
    virtual bool isEdge(int i,int j) =0;

    virtual int weight(int v1,int v2) =0;

    //Get and set mark to v;
    virtual int getMark(int v) =0;
    virtual int setMark(int v,int val) =0;

};