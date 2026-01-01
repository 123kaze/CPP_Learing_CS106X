#include "grapgh1.h"
#include <iostream>
#include <vector>
#include <stdexcept>
#include <queue>

using namespace std;

class Graphm : public Graph {
private:
    int numVertices;
    int numEdges;
    bool directed;
    vector<vector<int>> adjMatrix;
    vector<int> mark;  // For marking vertices during traversal
    
public:
    // Constructor
    Graphm(int n = 0, bool isDirected = false) : numVertices(n), numEdges(0), directed(isDirected) {
        if (n < 0) {
            throw invalid_argument("Number of vertices cannot be negative");
        }
        
        // Initialize adjacency matrix
        adjMatrix.resize(n, vector<int>(n, 0));
        
        // Initialize mark array
        mark.resize(n, 0);
    }
    
    // Initialize a graph with n vertices
    virtual void Init(int n) override {
        if (n < 0) {
            throw invalid_argument("Number of vertices cannot be negative");
        }
        
        numVertices = n;
        numEdges = 0;
        adjMatrix.resize(n, vector<int>(n, 0));
        mark.resize(n, 0);
    }
    
    // Return the number of vertices
    virtual int n() override {
        return numVertices;
    }
    
    // Return the number of edges
    virtual int e() override {
        return numEdges;
    }
    
    // Return v's first neighbor
    virtual int first(int v) override {
        if (v < 0 || v >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        for (int i = 0; i < numVertices; i++) {
            if (adjMatrix[v][i] != 0) {
                return i;
            }
        }
        
        return numVertices; // Return n if no neighbor
    }
    
    // Return v's next neighbor after w
    virtual int next(int v, int w) override {
        if (v < 0 || v >= numVertices || w < 0 || w >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        for (int i = w + 1; i < numVertices; i++) {
            if (adjMatrix[v][i] != 0) {
                return i;
            }
        }
        
        return numVertices; // Return n if no more neighbors
    }
    
    // Set the weight for an edge
    virtual void setEdge(int v1, int v2, int wgt) override {
        if (v1 < 0 || v1 >= numVertices || v2 < 0 || v2 >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        if (wgt <= 0) {
            throw invalid_argument("Edge weight must be positive");
        }
        
        // Check if edge already exists
        if (adjMatrix[v1][v2] == 0) {
            numEdges++;
        }
        
        adjMatrix[v1][v2] = wgt;
        
        // If undirected graph, set symmetric edge
        if (!directed) {
            if (adjMatrix[v2][v1] == 0) {
                // Don't double count edges for undirected graph
                // We already incremented numEdges above
            }
            adjMatrix[v2][v1] = wgt;
        }
    }
    
    // Delete edge
    virtual void delEdge(int v1, int v2) override {
        if (v1 < 0 || v1 >= numVertices || v2 < 0 || v2 >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        if (adjMatrix[v1][v2] != 0) {
            numEdges--;
        }
        
        adjMatrix[v1][v2] = 0;
        
        // If undirected graph, delete symmetric edge
        if (!directed) {
            adjMatrix[v2][v1] = 0;
        }
    }
    
    // Determine if an edge is in a graph
    virtual bool isEdge(int i, int j) override {
        if (i < 0 || i >= numVertices || j < 0 || j >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        return adjMatrix[i][j] != 0;
    }
    
    // Get the weight of an edge
    virtual int weight(int v1, int v2) override {
        if (v1 < 0 || v1 >= numVertices || v2 < 0 || v2 >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        return adjMatrix[v1][v2];
    }
    
    // Get mark for vertex v
    virtual int getMark(int v) override {
        if (v < 0 || v >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        return mark[v];
    }
    
    // Set mark for vertex v
    virtual void setMark(int v, int val) override {
        if (v < 0 || v >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        mark[v] = val;
    }
    
    // Additional utility functions (not part of Graph interface)
    
    // Check if graph is directed
    bool isDirected() const {
        return directed;
    }
    
    // Print adjacency matrix
    void printAdjMatrix() const {
        cout << "Adjacency Matrix (" << numVertices << " vertices, " 
             << numEdges << " edges, "
             << (directed ? "directed" : "undirected") << "):" << endl;
        
        // Print column indices
        cout << "   ";
        for (int i = 0; i < numVertices; i++) {
            cout << i << " ";
        }
        cout << endl;
        
        // Print matrix
        for (int i = 0; i < numVertices; i++) {
            cout << i << ": ";
            for (int j = 0; j < numVertices; j++) {
                cout << adjMatrix[i][j] << " ";
            }
            cout << endl;
        }
    }
    
    // Get neighbors of vertex v
    vector<int> getNeighbors(int v) const {
        if (v < 0 || v >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        vector<int> neighbors;
        for (int i = 0; i < numVertices; i++) {
            if (adjMatrix[v][i] != 0) {
                neighbors.push_back(i);
            }
        }
        
        return neighbors;
    }
    
    // Get degree of vertex v (out-degree for directed graphs)
    int getDegree(int v) const {
        if (v < 0 || v >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        int degree = 0;
        for (int i = 0; i < numVertices; i++) {
            if (adjMatrix[v][i] != 0) {
                degree++;
            }
        }
        
        return degree;
    }
    
    // Get in-degree of vertex v (only meaningful for directed graphs)
    int getInDegree(int v) const {
        if (v < 0 || v >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        if (!directed) {
            return getDegree(v); // For undirected graphs, in-degree = out-degree
        }
        
        int inDegree = 0;
        for (int i = 0; i < numVertices; i++) {
            if (adjMatrix[i][v] != 0) {
                inDegree++;
            }
        }
        
        return inDegree;
    }
};

// Test program
int main() {
    try {
        cout << "Testing Graphm class (adjacency matrix implementation)" << endl;
        cout << "======================================================" << endl;
        
        // Create an undirected graph with 5 vertices
        Graphm g(5, false);
        
        // Test Init method
        cout << "\n1. Testing Init method:" << endl;
        g.Init(5);
        cout << "   Number of vertices: " << g.n() << endl;
        cout << "   Number of edges: " << g.e() << endl;
        
        // Test setEdge method
        cout << "\n2. Testing setEdge method:" << endl;
        g.setEdge(0, 1, 1);
        g.setEdge(0, 2, 1);
        g.setEdge(1, 2, 1);
        g.setEdge(2, 3, 1);
        g.setEdge(3, 4, 1);
        g.setEdge(1, 4, 3); // Weighted edge
        
        cout << "   After adding 6 edges:" << endl;
        cout << "   Number of edges: " << g.e() << endl;
        g.printAdjMatrix();
        
        // Test isEdge method
        cout << "\n3. Testing isEdge method:" << endl;
        cout << "   Edge (0,1) exists: " << (g.isEdge(0, 1) ? "Yes" : "No") << endl;
        cout << "   Edge (0,4) exists: " << (g.isEdge(0, 4) ? "Yes" : "No") << endl;
        
        // Test weight method
        cout << "\n4. Testing weight method:" << endl;
        cout << "   Weight of edge (1,4): " << g.weight(1, 4) << endl;
        cout << "   Weight of edge (0,1): " << g.weight(0, 1) << endl;
        
        // Test first and next methods
        cout << "\n5. Testing first and next methods:" << endl;
        int v = 1;
        cout << "   Neighbors of vertex " << v << ": ";
        for (int w = g.first(v); w < g.n(); w = g.next(v, w)) {
            cout << w << " ";
        }
        cout << endl;
        
        // Test getMark and setMark methods
        cout << "\n6. Testing getMark and setMark methods:" << endl;
        g.setMark(0, 1);
        g.setMark(1, 2);
        cout << "   Mark of vertex 0: " << g.getMark(0) << endl;
        cout << "   Mark of vertex 1: " << g.getMark(1) << endl;
        cout << "   Mark of vertex 2: " << g.getMark(2) << " (default 0)" << endl;
        
        // Test delEdge method
        cout << "\n7. Testing delEdge method:" << endl;
        cout << "   Before deleting edge (1,2):" << endl;
        cout << "   Edge (1,2) exists: " << (g.isEdge(1, 2) ? "Yes" : "No") << endl;
        cout << "   Number of edges: " << g.e() << endl;
        
        g.delEdge(1, 2);
        
        cout << "   After deleting edge (1,2):" << endl;
        cout << "   Edge (1,2) exists: " << (g.isEdge(1, 2) ? "Yes" : "No") << endl;
        cout << "   Number of edges: " << g.e() << endl;
        g.printAdjMatrix();
        
        // Test directed graph
        cout << "\n8. Testing directed graph:" << endl;
        Graphm dg(4, true);
        dg.setEdge(0, 1, 1);
        dg.setEdge(0, 2, 1);
        dg.setEdge(1, 3, 1);
        dg.setEdge(2, 3, 1);
        
        dg.printAdjMatrix();
        cout << "   Out-degree of vertex 0: " << dg.getDegree(0) << endl;
        cout << "   In-degree of vertex 3: " << dg.getInDegree(3) << endl;
        
        cout << "\nAll tests completed successfully!" << endl;
        
    } catch (const exception& e) {
        cerr << "Error: " << e.what() << endl;
        return 1;
    }
    
    return 0;
}
