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

    # Half the traffic is H-V-H.
    hvh_weight = 0.5
    if uy == vy:
        add_path(edges, u, v, hvh_weight)
    else:
        per_col = hvh_weight / K
        for mid_x in range(K):
            row_node = uy * K + mid_x
            col_node = vy * K + mid_x
            add_path(edges, u, row_node, per_col)
            add_path(edges, row_node, col_node, per_col)
            add_path(edges, col_node, v, per_col)

    # Half the traffic is V-H-V.
    vhv_weight = 0.5
    if ux == vx:
        add_path(edges, u, v, vhv_weight)
    else:
        per_row = vhv_weight / K
        for mid_y in range(K):
            col_node = mid_y * K + ux
            row_node = mid_y * K + vx
            add_path(edges, u, col_node, per_row)
            add_path(edges, col_node, row_node, per_row)
            add_path(edges, row_node, v, per_row)

    return dict(edges)


pair_contributions = {
    (u, v): racke_pair_contribution(u, v)
    for u in NODES
    for v in NODES
    if u != v
}

max_perm_load = 0.0
max_perm = None
for perm in itertools.permutations(NODES):
    edge_counts = collections.defaultdict(float)
    for u in NODES:
        v = perm[u]
        if u == v:
            continue
        for edge, load in pair_contributions[(u, v)].items():
            edge_counts[edge] += load
    if not edge_counts:
        continue
    current_max = max(edge_counts.values())
    if current_max > max_perm_load:
        max_perm_load = current_max
        max_perm = perm

print(f"Max Permutation Edge Load: {max_perm_load:.10f}")
print(f"Expected Edge Load Bound: {EXPECTED_MAX_LOAD:.10f}")
print(f"Guaranteed Injection Rate (1/Max Load): {1.0/max_perm_load:.10f}")
print(f"Expected Injection Bound (6/7): {6.0/7.0:.10f}")
if max_perm is not None:
    print(f"Worst Permutation: {max_perm}")

if abs(max_perm_load - EXPECTED_MAX_LOAD) <= TOL:
    print("PASS: worst-case permutation edge load matches 7/6.")
else:
    raise SystemExit(
        f"FAIL: expected {EXPECTED_MAX_LOAD:.10f}, got {max_perm_load:.10f}"
    )
