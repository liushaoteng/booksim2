import itertools
import collections

# 3x3 Mesh nodes: 0..8
# (x, y) = (node % 3, node // 3)

def get_dist(u, v):
    ux, uy = u % 3, u // 3
    vx, vy = v % 3, v // 3
    return abs(ux-vx) + abs(uy-vy)

def get_path_xy(u, v):
    ux, uy = u % 3, u // 3
    vx, vy = v % 3, v // 3
    path = []
    # X-first: move horizontally
    curr_x, curr_y = ux, uy
    while curr_x != vx:
        step = 1 if vx > curr_x else -1
        next_x = curr_x + step
        edge = (curr_y * 3 + curr_x, curr_y * 3 + next_x)
        path.append(edge)
        curr_x = next_x
    # Move vertically
    while curr_y != vy:
        step = 1 if vy > curr_y else -1
        next_y = curr_y + step
        edge = (curr_y * 3 + curr_x, next_y * 3 + curr_x)
        path.append(edge)
        curr_y = next_y
    return path

def run_analysis():
    nodes = list(range(9))
    perms = list(itertools.permutations(nodes))
    total_perms = len(perms)
    print(f"Total permutations: {total_perms}")
    
    # Precompute edge contributions for each node pair (u,v) using Rule 2 & 3
    # Rule 2: If same row or column, route XY directly.
    # Rule 3: If different row and column, split 50/50:
    #   Path A: Intermediate node in same row as U and same column as V.
    #   Path B: Intermediate node in same column as U and same row as V.
    
    pair_contributions = {}
    for u in nodes:
        ux, uy = u % 3, u // 3
        for v in nodes:
            if u == v: continue
            vx, vy = v % 3, v // 3
            edges = collections.defaultdict(float)
            if ux == vx or uy == vy:
                # Direct XY
                for e in get_path_xy(u, v):
                    edges[e] += 1.0
            else:
                # Split 50/50
                w1 = vy * 3 + ux # Same col as U, same row as V
                w2 = uy * 3 + vx # Same row as U, same col as V
                # Path A: U -> w1 -> V (All XY)
                for e in get_path_xy(u, w1): edges[e] += 0.5
                for e in get_path_xy(w1, v): edges[e] += 0.5
                # Path B: U -> w2 -> V (All XY)
                for e in get_path_xy(u, w2): edges[e] += 0.5
                for e in get_path_xy(w2, v): edges[e] += 0.5
            pair_contributions[(u, v)] = dict(edges)

    max_worst_load = 0.0
    
    # For speed, we just check the load-balanced case (uniform) first
    edge_totals = collections.defaultdict(float)
    for (u, v), edges in pair_contributions.items():
        for e, load in edges.items():
            edge_totals[e] += load / 9.0
            
    print("\nSteady State (Uniform) Edge Loads:")
    unique_loads = sorted(list(set(edge_totals.values())), reverse=True)
    for l in unique_loads:
        print(f"Load {l:.4f} (Theoretical: {l*6:.2f}/6)")
    
    max_worst_load = max(edge_totals.values())
    print(f"\nWorst-case Edge Load: {max_worst_load:.4f}")
    print(f"Bisection Limit: {1.0/max_worst_load:.4f}")

if __name__ == "__main__":
    run_analysis()
