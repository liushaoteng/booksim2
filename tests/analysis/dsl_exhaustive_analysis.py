import itertools
import collections

# Nodes: 0..8
def get_path_xy(u, v):
    ux, uy = u % 3, u // 3
    vx, vy = v % 3, v // 3
    path = []
    curr_x, curr_y = ux, uy
    while curr_x != vx:
        step = 1 if vx > curr_x else -1
        next_x = curr_x + step
        edge = (curr_y * 3 + curr_x, curr_y * 3 + next_x)
        path.append(edge)
        curr_x = next_x
    while curr_y != vy:
        step = 1 if vy > curr_y else -1
        next_y = curr_y + step
        edge = (curr_y * 3 + curr_x, next_y * 3 + curr_x)
        path.append(edge)
        curr_y = next_y
    return path

def run_analysis():
    # VLB logic: U -> W -> V (Random intermediate W)
    # Average edge load = 1/9 * sum_{W} (U->W path + W->V path)
    nodes = list(range(9))
    pair_contributions = {}
    for u in nodes:
        for v in nodes:
            if u == v: continue
            edge_sum = collections.defaultdict(float)
            for w in nodes:
                # Path U->W
                for e in get_path_xy(u, w): edge_sum[e] += 1.0/9.0
                # Path W->V
                for e in get_path_xy(w, v): edge_sum[e] += 1.0/9.0
            pair_contributions[(u, v)] = dict(edge_sum)

    # Worst-case Permutation (Uniform check)
    edge_totals = collections.defaultdict(float)
    for (u, v), edges in pair_contributions.items():
        for e, load in edges.items():
            edge_totals[e] += load / 9.0
            
    print("\nVLB Steady State (Uniform) Edge Loads on 3x3 Mesh:")
    unique_loads = sorted(list(set(edge_totals.values())), reverse=True)
    for l in unique_loads:
        print(f"Load {l:.4f} (Theoretical: {l*9:.2f}/9)")
    
    max_worst_load = max(edge_totals.values())
    print(f"\nWorst-case Edge Load: {max_worst_load:.4f}")
    print(f"Bisection Limit: {1.0/max_worst_load:.4f}")

if __name__ == "__main__":
    run_analysis()
