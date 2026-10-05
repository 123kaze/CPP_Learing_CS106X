import itertools
def solve():
    grid = [input().strip() for _ in range(8)]
    nodes = []
    for r in range(8):
        for c in range(8):
            if grid[r][c] == '#':
                nodes.append((r, c))
    if len(nodes) <= 1:
        print(0)
        return
    mintime = float('inf')
    for order in itertools.permutations(nodes):
        current = 0
        for i in range(1, len(order)):
            curr_node = order[i]
            built = order[:i]
            maxdist = 0
            for built in built:
                dist = max(abs(curr_node[0] - built[0]), abs(curr_node[1] - built[1]))
                maxdist = max(maxdist, dist)

            current += maxdist
        mintime = min(mintime, current)
    print(mintime)

if __name__ == "__main__":
    solve()
