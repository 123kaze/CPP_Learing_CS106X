#ifndef GRAPH_H
#define GRAPH_H

#include <iostream>
#include <vector>

class Graph {
private:
    // Protect assignment and copy constructor
    void operator=(const Graph&) {}
    Graph(const Graph&) {}
    
public:
    // Constructor and destructor
    Graph() {}
    virtual ~Graph() {}
    
    // Initialize a graph with n vertices
    virtual void Init(int n) = 0;
    
    // Return the number of vertices and edges
    virtual int n() = 0;
    virtual int e() = 0;
    
    // Return v's first neighbor
    virtual int first(int v) = 0;
    
    // Return v's next neighbor after w
    virtual int next(int v, int w) = 0;
    
    // Set the weight for an edge
    // v1, v2: vertices
    // wgt: Edge weight
    virtual void setEdge(int v1, int v2, int wgt) = 0;
    
    // Delete edge
    // v1, v2: the vertices
    virtual void delEdge(int v1, int v2) = 0;
    
    // Determine if an edge is in a graph
    virtual bool isEdge(int i, int j) = 0;
    
    // Get the weight of an edge
    virtual int weight(int v1, int v2) = 0;
    
    // Get and set mark for vertex v
    virtual int getMark(int v) = 0;
    virtual void setMark(int v, int val) = 0;
};

#endif // GRAPH_H
