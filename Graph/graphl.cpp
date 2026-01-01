#include "grapgh1.h"
#include <iostream>
#include <vector>
#include <stdexcept>
#include <queue>
#include <list>
#include <algorithm>

using namespace std;

// Edge structure to represent an edge in the graph
struct Edge {
    int src;    // Source vertex (needed for single list representation)
    int dest;   // Destination vertex
    int weight; // Edge weight
    
    Edge(int s, int d, int w) : src(s), dest(d), weight(w) {}
    
    // For comparison when searching in list
    bool operator==(const Edge& other) const {
        return src == other.src && dest == other.dest;
    }
    
    // Check if this edge connects vertex v
    bool connects(int v) const {
        return src == v || dest == v;
    }
    
    // Get the other vertex in this edge
    int otherVertex(int v) const {
        if (src == v) return dest;
        if (dest == v) return src;
        throw invalid_argument("Vertex not part of this edge");
    }
    
    // Check if this is an outgoing edge from v
    bool isOutgoingFrom(int v) const {
        return src == v;
    }
    
    // Check if this is an incoming edge to v
    bool isIncomingTo(int v) const {
        return dest == v;
    }
};

// Graphl class - edge list implementation using a single list<Edge>
class Graphl : public Graph {
private:
    int numVertices;
    int numEdges;
    bool directed;
    list<Edge> edgeList;  // Single list containing all edges
    vector<int> mark;     // For marking vertices during traversal
    
    // Helper function to find an edge in the edge list
    list<Edge>::iterator findEdge(int v1, int v2) {
        return find_if(edgeList.begin(), edgeList.end(),
                      [v1, v2, this](const Edge& e) {
                          if (directed) {
                              return e.src == v1 && e.dest == v2;
                          } else {
                              return (e.src == v1 && e.dest == v2) ||
                                     (e.src == v2 && e.dest == v1);
                          }
                      });
    }
    
    // Helper function to find an edge (const version)
    list<Edge>::const_iterator findEdge(int v1, int v2) const {
        return find_if(edgeList.begin(), edgeList.end(),
                      [v1, v2, this](const Edge& e) {
                          if (directed) {
                              return e.src == v1 && e.dest == v2;
                          } else {
                              return (e.src == v1 && e.dest == v2) ||
                                     (e.src == v2 && e.dest == v1);
                          }
                      });
    }
    
    // Helper function to get all edges incident to vertex v
    vector<Edge> getIncidentEdges(int v) const {
        vector<Edge> incident;
        for (const Edge& e : edgeList) {
            if (e.connects(v)) {
                incident.push_back(e);
            }
        }
        return incident;
    }
    
    // Helper function to get outgoing edges from vertex v
    vector<Edge> getOutgoingEdges(int v) const {
        vector<Edge> outgoing;
        for (const Edge& e : edgeList) {
            if (directed) {
                if (e.isOutgoingFrom(v)) {
                    outgoing.push_back(e);
                }
            } else {
                if (e.connects(v)) {
                    outgoing.push_back(e);
                }
            }
        }
        return outgoing;
    }
    
    // Helper function to get incoming edges to vertex v
    vector<Edge> getIncomingEdges(int v) const {
        vector<Edge> incoming;
        for (const Edge& e : edgeList) {
            if (directed) {
                if (e.isIncomingTo(v)) {
                    incoming.push_back(e);
                }
            } else {
                if (e.connects(v)) {
                    incoming.push_back(e);
                }
            }
        }
        return incoming;
    }
    
public:
    // Constructor
    Graphl(int n = 0, bool isDirected = false) : numVertices(n), numEdges(0), directed(isDirected) {
        if (n < 0) {
            throw invalid_argument("Number of vertices cannot be negative");
        }
        
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
        edgeList.clear();
        mark.clear();
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
        
        // Find the first edge incident to v
        for (const Edge& e : edgeList) {
            if (e.connects(v)) {
                return e.otherVertex(v);
            }
        }
        
        return numVertices; // Return n if no neighbor
    }
    
    // Return v's next neighbor after w
    virtual int next(int v, int w) override {
        if (v < 0 || v >= numVertices || w < 0 || w >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        bool foundW = false;
        for (const Edge& e : edgeList) {
            if (e.connects(v)) {
                int other = e.otherVertex(v);
                if (foundW) {
                    return other; // Return the neighbor after w
                }
                if (other == w) {
                    foundW = true;
                }
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
        auto it = findEdge(v1, v2);
        if (it != edgeList.end()) {
            // Update existing edge weight
            it->weight = wgt;
        } else {
            // Add new edge
            if (directed) {
                edgeList.push_front(Edge(v1, v2, wgt));
            } else {
                // For undirected graph, we store edge with src < dest for consistency
                if (v1 <= v2) {
                    edgeList.push_front(Edge(v1, v2, wgt));
                } else {
                    edgeList.push_front(Edge(v2, v1, wgt));
                }
            }
            numEdges++;
        }
    }
    
    // Delete edge
    virtual void delEdge(int v1, int v2) override {
        if (v1 < 0 || v1 >= numVertices || v2 < 0 || v2 >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        auto it = findEdge(v1, v2);
        if (it != edgeList.end()) {
            edgeList.erase(it);
            numEdges--;
        }
    }
    
    // Determine if an edge is in a graph
    virtual bool isEdge(int i, int j) override {
        if (i < 0 || i >= numVertices || j < 0 || j >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        return findEdge(i, j) != edgeList.end();
    }
    
    // Get the weight of an edge
    virtual int weight(int v1, int v2) override {
        if (v1 < 0 || v1 >= numVertices || v2 < 0 || v2 >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        auto it = findEdge(v1, v2);
        if (it != edgeList.end()) {
            return it->weight;
        }
        
        return 0; // Return 0 if edge doesn't exist (consistent with adjacency matrix)
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
    
    // Print edge list
    void printEdgeList() const {
        cout << "Edge List (" << numVertices << " vertices, " 
             << numEdges << " edges, "
             << (directed ? "directed" : "undirected") << "):" << endl;
        
        for (const Edge& e : edgeList) {
            if (directed) {
                cout << "  " << e.src << " -> " << e.dest << " (weight: " << e.weight << ")" << endl;
            } else {
                cout << "  " << e.src << " -- " << e.dest << " (weight: " << e.weight << ")" << endl;
            }
        }
    }
    
    // Get neighbors of vertex v
    vector<int> getNeighbors(int v) const {
        if (v < 0 || v >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        vector<int> neighbors;
        for (const Edge& e : edgeList) {
            if (e.connects(v)) {
                neighbors.push_back(e.otherVertex(v));
            }
        }
        
        // Remove duplicates (for undirected graphs where edges might be traversed twice)
        sort(neighbors.begin(), neighbors.end());
        neighbors.erase(unique(neighbors.begin(), neighbors.end()), neighbors.end());
        
        return neighbors;
    }
    
    // Get degree of vertex v (out-degree for directed graphs)
    int getDegree(int v) const {
        if (v < 0 || v >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        if (directed) {
            return getOutgoingEdges(v).size();
        } else {
            int degree = 0;
            for (const Edge& e : edgeList) {
                if (e.connects(v)) {
                    degree++;
                }
            }
            return degree;
        }
    }
    
    // Get in-degree of vertex v (only meaningful for directed graphs)
    int getInDegree(int v) const {
        if (v < 0 || v >= numVertices) {
            throw out_of_range("Vertex index out of range");
        }
        
        if (!directed) {
            return getDegree(v); // For undirected graphs, in-degree = out-degree
        }
        
        return getIncomingEdges(v).size();
    }
};

// Function declarations
void DFS_helper(Graphl* G, int v);
void DFS(Graphl* G, int v);
void DFS_complete(Graphl* G);
void PreVisit(Graph* G, int v);
void PostVisit(Graph* G, int v);
void DFS_explicit(Graph* G, int v);
void DFS_explicit_wrapper(Graphl* G, int v);
void DFS_explicit_complete(Graphl* G);

// Test program
int main() {
    try {
        cout << "Testing Graphl class (edge list implementation using single list<Edge>)" << endl;
        cout << "=======================================================================" << endl;
        
        // Create an undirected graph with 5 vertices
        Graphl g(5, false);
        
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
        g.printEdgeList();
        
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
        g.printEdgeList();
        
        // Test directed graph
        cout << "\n8. Testing directed graph:" << endl;
        Graphl dg(4, true);
        dg.setEdge(0, 1, 1);
        dg.setEdge(0, 2, 1);
        dg.setEdge(1, 3, 1);
        dg.setEdge(2, 3, 1);
        
        dg.printEdgeList();
        cout << "   Out-degree of vertex 0: " << dg.getDegree(0) << endl;
        cout << "   In-degree of vertex 3: " << dg.getInDegree(3) << endl;
        
        // Test edge weight update
        cout << "\n9. Testing edge weight update:" << endl;
        cout << "   Before update, weight of (0,1): " << dg.weight(0, 1) << endl;
        dg.setEdge(0, 1, 5);  // Update weight
        cout << "   After update, weight of (0,1): " << dg.weight(0, 1) << endl;
        
        // Test with larger graph
        cout << "\n10. Testing with larger graph:" << endl;
        Graphl largeGraph(100, false);
        // Add many edges
        for (int i = 0; i < 500; i++) {
            int v1 = rand() % 100;
            int v2 = rand() % 100;
            if (v1 != v2) {
                largeGraph.setEdge(v1, v2, 1);
            }
        }
        cout << "   Large graph created with " << largeGraph.n() << " vertices and " 
             << largeGraph.e() << " edges." << endl;
        
        // Test neighbor retrieval
        int testVertex = rand() % 100;
        vector<int> neighbors = largeGraph.getNeighbors(testVertex);
        cout << "   Vertex " << testVertex << " has " << neighbors.size() << " neighbors." << endl;
        
        // Test DFS
        cout << "\n11. Testing DFS traversal:" << endl;
        
        // Create a simple connected graph for DFS testing
        Graphl dfsGraph(8, false);
        dfsGraph.setEdge(0, 1, 1);
        dfsGraph.setEdge(0, 2, 1);
        dfsGraph.setEdge(1, 3, 1);
        dfsGraph.setEdge(1, 4, 1);
        dfsGraph.setEdge(2, 5, 1);
        dfsGraph.setEdge(2, 6, 1);
        dfsGraph.setEdge(3, 7, 1);
        dfsGraph.setEdge(4, 7, 1);
        
        cout << "   Graph structure:" << endl;
        dfsGraph.printEdgeList();
        
        // Test DFS from vertex 0
        cout << "\n   DFS from vertex 0:" << endl;
        DFS(&dfsGraph, 0);
        
        // Test DFS from vertex 3
        cout << "\n   DFS from vertex 3:" << endl;
        DFS(&dfsGraph, 3);
        
        // Test complete DFS (should be same as from 0 since graph is connected)
        cout << "\n   Complete DFS traversal:" << endl;
        DFS_complete(&dfsGraph);
        
        // Test DFS on disconnected graph
        cout << "\n   Testing DFS on disconnected graph:" << endl;
        Graphl disconnectedGraph(6, false);
        // First component: vertices 0,1,2
        disconnectedGraph.setEdge(0, 1, 1);
        disconnectedGraph.setEdge(1, 2, 1);
        // Second component: vertices 3,4,5
        disconnectedGraph.setEdge(3, 4, 1);
        disconnectedGraph.setEdge(4, 5, 1);
        
        cout << "   Disconnected graph structure:" << endl;
        disconnectedGraph.printEdgeList();
        
        cout << "\n   Complete DFS on disconnected graph:" << endl;
        DFS_complete(&disconnectedGraph);
        
        // Test DFS with explicit backtracking
        cout << "\n12. Testing DFS with explicit backtracking:" << endl;
        
        // Create a simple graph for explicit backtracking DFS testing
        Graphl explicitGraph(6, false);
        explicitGraph.setEdge(0, 1, 1);
        explicitGraph.setEdge(0, 2, 1);
        explicitGraph.setEdge(1, 3, 1);
        explicitGraph.setEdge(1, 4, 1);
        explicitGraph.setEdge(2, 5, 1);
        
        cout << "   Graph structure for explicit backtracking:" << endl;
        explicitGraph.printEdgeList();
        
        // Test explicit backtracking DFS from vertex 0
        cout << "\n   DFS with explicit backtracking from vertex 0:" << endl;
        DFS_explicit_wrapper(&explicitGraph, 0);
        
        // Test explicit backtracking DFS from vertex 1
        cout << "\n   DFS with explicit backtracking from vertex 1:" << endl;
        DFS_explicit_wrapper(&explicitGraph, 1);
        
        // Test complete explicit backtracking DFS
        cout << "\n   Complete DFS with explicit backtracking:" << endl;
        DFS_explicit_complete(&explicitGraph);
        
        cout << "\nAll tests completed successfully!" << endl;
        
    } catch (const exception& e) {
        cerr << "Error: " << e.what() << endl;
        return 1;
    }
    
    return 0;
}

// DFS helper function (recursive) using graph marks
void DFS_helper(Graphl* G, int v) {
    // Mark current vertex as visited (mark = 1)
    G->setMark(v, 1);
    cout << v << " ";  // Process vertex (print it)
    
    // Get all neighbors of vertex v
    vector<int> neighbors = G->getNeighbors(v);
    
    // Recursively visit all unvisited neighbors
    for (int neighbor : neighbors) {
        if (G->getMark(neighbor) == 0) {  // Not visited
            DFS_helper(G, neighbor);
        }
    }
}

// Depth First Search starting from vertex v
void DFS(Graphl* G, int v) {
    if (G == nullptr) {
        throw invalid_argument("Graph pointer cannot be null");
    }
    
    if (v < 0 || v >= G->n()) {
        throw out_of_range("Vertex index out of range");
    }
    
    // Clear all marks (mark = 0 means not visited)
    for (int i = 0; i < G->n(); i++) {
        G->setMark(i, 0);
    }
    
    cout << "DFS starting from vertex " << v << ": ";
    
    // Start DFS traversal
    DFS_helper(G, v);
    
    cout << endl;
}

// DFS for entire graph (handles disconnected graphs)
void DFS_complete(Graphl* G) {
    if (G == nullptr) {
        throw invalid_argument("Graph pointer cannot be null");
    }
    
    // Clear all marks (mark = 0 means not visited)
    for (int i = 0; i < G->n(); i++) {
        G->setMark(i, 0);
    }
    
    cout << "DFS traversal of entire graph: ";
    
    // Visit all vertices
    for (int v = 0; v < G->n(); v++) {
        if (G->getMark(v) == 0) {  // Not visited
            DFS_helper(G, v);
        }
    }
    
    cout << endl;
}

// PreVisit function - called before processing a vertex
void PreVisit(Graph* G, int v) {
    cout << "Entering vertex " << v << endl;
}

// PostVisit function - called after processing a vertex (backtracking)
void PostVisit(Graph* G, int v) {
    cout << "Leaving vertex " << v << " (backtracking)" << endl;
}

// DFS with explicit backtracking using PreVisit and PostVisit
void DFS_explicit(Graph* G, int v) {
    PreVisit(G, v);
    G->setMark(v, 1);
    
    for (int w = G->first(v); w < G->n(); w = G->next(v, w)) {
        if (G->getMark(w) == 0) {
            DFS_explicit(G, w);
        }
    }
    
    PostVisit(G, v);
}

// Wrapper function for DFS with explicit backtracking
void DFS_explicit_wrapper(Graphl* G, int v) {
    if (G == nullptr) {
        throw invalid_argument("Graph pointer cannot be null");
    }
    
    if (v < 0 || v >= G->n()) {
        throw out_of_range("Vertex index out of range");
    }
    
    // Clear all marks (mark = 0 means not visited)
    for (int i = 0; i < G->n(); i++) {
        G->setMark(i, 0);
    }
    
    cout << "DFS with explicit backtracking starting from vertex " << v << ":" << endl;
    DFS_explicit(G, v);
    cout << endl;
}

// DFS for entire graph with explicit backtracking
void DFS_explicit_complete(Graphl* G) {
    if (G == nullptr) {
        throw invalid_argument("Graph pointer cannot be null");
    }
    
    // Clear all marks (mark = 0 means not visited)
    for (int i = 0; i < G->n(); i++) {
        G->setMark(i, 0);
    }
    
    cout << "DFS traversal of entire graph with explicit backtracking:" << endl;
    
    // Visit all vertices
    for (int v = 0; v < G->n(); v++) {
        if (G->getMark(v) == 0) {  // Not visited
            DFS_explicit(G, v);
        }
    }
    
    cout << endl;
}
