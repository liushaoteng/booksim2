import networkx as nx # type: ignore
import itertools

def get_path_xy(u, v):
    ux, uy = u % 3, u // 3
    vx, vy = v % 3, v // 3
    path = []
    curr_x, curr_y = ux, uy
    while curr_x != vx:
        step = 1 if vx > curr_x else -1
        next_x = curr_x + step
        edge = (curr_y * 3 + curr_x, curr_y * 3 + next_x)
        path.append(tuple(sorted(edge)))
        curr_x = next_x
    while curr_y != vy:
        step = 1 if vy > curr_y else -1
        next_y = curr_y + step
        edge = (curr_y * 3 + curr_x, next_y * 3 + curr_x)
        path.append(tuple(sorted(edge)))
        curr_y = next_y
    return path

def run_analysis():
    G = nx.grid_2d_graph(3, 3)
    nodes = list(range(9))
    
    # 3x3 Mesh edges (12 total for Mesh)
    edges = []
    for u in nodes:
        ux, uy = u % 3, u // 3
        if ux < 2: edges.append(tuple(sorted((u, u+1))))
        if uy < 2: edges.append(tuple(sorted((u, u+3))))
    
    # DSL Analysis
    edge_loads = {e: 0.0 for e in edges}
    for u, v in itertools.permutations(nodes, 2):
        for w in nodes:
            # U -> W -> V
            p1 = get_path_xy(u, w)
            p2 = get_path_xy(w, v)
            for e in p1: edge_loads[e] += 1.0/9.0
            for e in p2: edge_loads[e] += 1.0/9.0
            
    # Normalize per source node (9 source nodes)
    for e in edge_loads:
        edge_loads[e] /= 9.0
        
    print("DSL 3x3 Mesh Edge Loads (Theoretical):")
    for e, l in sorted(edge_loads.items(), key=lambda x: x[1], reverse=True):
        print(f"Edge {e}: {l:.4f} (Load factor: {l*9:.2f}/9)")

    max_load = max(edge_loads.values())
    print(f"\nMax Load: {max_load:.4f}")
    print(f"Bisection Limit: {1.0/max_load:.4f}")

if __name__ == "__main__":
    run_analysis()

