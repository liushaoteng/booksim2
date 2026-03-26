import collections
import itertools

K = 3
NODES = list(range(K * K))
EXPECTED_MAX_LOAD = 7.0 / 6.0
TOL = 1e-9


def get_path_xy(u, v):
    ux, uy = u % K, u // K
    vx, vy = v % K, v // K
    path = []
    curr_x, curr_y = ux, uy
    while curr_x != vx:
        step = 1 if vx > curr_x else -1
        next_x = curr_x + step
        path.append((curr_y * K + curr_x, curr_y * K + next_x))
        curr_x = next_x
    while curr_y != vy:
        step = 1 if vy > curr_y else -1
        next_y = curr_y + step
        path.append((curr_y * K + curr_x, next_y * K + curr_x))
        curr_y = next_y
    return path


def add_path(edges, u, v, weight):
    for edge in get_path_xy(u, v):
        edges[edge] += weight


def racke_pair_contribution(u, v):
    ux, uy = u % K, u // K
    vx, vy = v % K, v // K
    edges = collections.defaultdict(float)

    if u == v:
        return {}

    if uy == vy:
        add_path(edges, u, v, 0.5)
    else:
        for mid_x in range(K):
            row_node = uy * K + mid_x
            col_node = vy * K + mid_x
            add_path(edges, u, row_node, 1.0 / 6.0)
            add_path(edges, row_node, col_node, 1.0 / 6.0)
            add_path(edges, col_node, v, 1.0 / 6.0)

    if ux == vx:
        add_path(edges, u, v, 0.5)
    else:
        for mid_y in range(K):
            col_node = mid_y * K + ux
            row_node = mid_y * K + vx
            add_path(edges, u, col_node, 1.0 / 6.0)
            add_path(edges, col_node, row_node, 1.0 / 6.0)
            add_path(edges, row_node, v, 1.0 / 6.0)

    return dict(edges)


def run_analysis():
    perms = list(itertools.permutations(NODES))
    print(f"Total permutations: {len(perms)}")

    pair_contributions = {
        (u, v): racke_pair_contribution(u, v)
        for u in NODES
        for v in NODES
        if u != v
    }

    edge_totals = collections.defaultdict(float)
    for edges in pair_contributions.values():
        for edge, load in edges.items():
            edge_totals[edge] += load / len(NODES)

    print("\nSteady State (Uniform) Edge Loads:")
    for load in sorted(set(edge_totals.values()), reverse=True):
        print(f"Load {load:.4f}")

    max_uniform_load = max(edge_totals.values())
    print(f"\nWorst Uniform Edge Load: {max_uniform_load:.4f}")
    print(f"Uniform Injection Bound: {1.0/max_uniform_load:.4f}")

    max_perm_load = 0.0
    for perm in perms:
        edge_counts = collections.defaultdict(float)
        for u in NODES:
            v = perm[u]
            if u == v:
                continue
            for edge, load in pair_contributions[(u, v)].items():
                edge_counts[edge] += load
        if edge_counts:
            max_perm_load = max(max_perm_load, max(edge_counts.values()))

    print(f"\nWorst Permutation Edge Load: {max_perm_load:.4f}")
    print(f"Expected Permutation Bound: {EXPECTED_MAX_LOAD:.4f}")
    print(f"Permutation Injection Bound: {1.0/max_perm_load:.4f}")
    print(f"Expected Injection Bound: {6.0/7.0:.4f}")
    if abs(max_perm_load - EXPECTED_MAX_LOAD) <= TOL:
        print("PASS: worst-case permutation edge load matches 7/6.")
    else:
        raise SystemExit(
            f"FAIL: expected {EXPECTED_MAX_LOAD:.10f}, got {max_perm_load:.10f}"
        )

if __name__ == "__main__":
    run_analysis()
