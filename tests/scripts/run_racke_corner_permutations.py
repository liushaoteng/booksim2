#!/usr/bin/env python3

import argparse
import collections
import itertools
import json
import math
import os
import statistics
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from artifact_layout import timestamped_result_dir, write_readme

K = 3
NODES = tuple(range(K * K))
LOAD_BUCKETS = (
    7.0 / 6.0,
    1.0,
    5.0 / 6.0,
    2.0 / 3.0,
    0.5,
    0.0,
)
DEFAULT_CASES_PER_BUCKET = {
    7.0 / 6.0: 24,
    1.0: 12,
    5.0 / 6.0: 6,
    2.0 / 3.0: 3,
    0.5: 3,
    0.0: 1,
}
EPS = 1e-9


@dataclass(frozen=True)
class TheoryCase:
    permutation: tuple[int, ...]
    max_load: float
    second_max_load: float
    num_max_edges: int
    fixed_points: int
    same_row_pairs: int
    same_col_pairs: int
    avg_manhattan: float
    cycle_partition: tuple[int, ...]


def get_path_xy(u: int, v: int) -> list[tuple[int, int]]:
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


def add_path(edges: collections.defaultdict, u: int, v: int, weight: float) -> None:
    for edge in get_path_xy(u, v):
        edges[edge] += weight


def racke_pair_contribution(u: int, v: int) -> dict[tuple[int, int], float]:
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


PAIR_CONTRIBUTIONS = {
    (u, v): racke_pair_contribution(u, v)
    for u in NODES
    for v in NODES
    if u != v
}


def cycle_partition(perm: tuple[int, ...]) -> tuple[int, ...]:
    seen = [False] * len(perm)
    parts = []
    for start in range(len(perm)):
        if seen[start]:
            continue
        cur = start
        length = 0
        while not seen[cur]:
            seen[cur] = True
            cur = perm[cur]
            length += 1
        parts.append(length)
    return tuple(sorted(parts, reverse=True))


def analyze_permutation(perm: tuple[int, ...]) -> TheoryCase:
    edge_counts = collections.defaultdict(float)
    fixed_points = 0
    same_row_pairs = 0
    same_col_pairs = 0
    total_distance = 0

    for u, v in enumerate(perm):
        if u == v:
            fixed_points += 1
            continue
        if (u // K) == (v // K):
            same_row_pairs += 1
        if (u % K) == (v % K):
            same_col_pairs += 1
        total_distance += abs((u % K) - (v % K)) + abs((u // K) - (v // K))
        for edge, load in PAIR_CONTRIBUTIONS[(u, v)].items():
            edge_counts[edge] += load

    if edge_counts:
        loads = sorted(edge_counts.values(), reverse=True)
        max_load = loads[0]
        second_max_load = loads[1] if len(loads) > 1 else 0.0
        num_max_edges = sum(1 for load in loads if abs(load - max_load) <= EPS)
    else:
        max_load = 0.0
        second_max_load = 0.0
        num_max_edges = 0

    moving_flows = len(perm) - fixed_points
    avg_manhattan = total_distance / moving_flows if moving_flows else 0.0

    return TheoryCase(
        permutation=perm,
        max_load=max_load,
        second_max_load=second_max_load,
        num_max_edges=num_max_edges,
        fixed_points=fixed_points,
        same_row_pairs=same_row_pairs,
        same_col_pairs=same_col_pairs,
        avg_manhattan=avg_manhattan,
        cycle_partition=cycle_partition(perm),
    )


def feature_vector(case: TheoryCase) -> tuple[float, ...]:
    return (
        float(case.fixed_points),
        float(case.same_row_pairs),
        float(case.same_col_pairs),
        float(case.num_max_edges),
        float(case.avg_manhattan),
        float(case.second_max_load),
        float(sum(case.cycle_partition)),
        float(len(case.cycle_partition)),
        float(max(case.cycle_partition)),
    )


def normalize_vectors(cases: list[TheoryCase]) -> dict[tuple[int, ...], tuple[float, ...]]:
    vectors = [feature_vector(case) for case in cases]
    mins = [min(values) for values in zip(*vectors)]
    maxs = [max(values) for values in zip(*vectors)]
    normalized = {}
    for case, vec in zip(cases, vectors):
        out = []
        for value, min_value, max_value in zip(vec, mins, maxs):
            if abs(max_value - min_value) <= EPS:
                out.append(0.0)
            else:
                out.append((value - min_value) / (max_value - min_value))
        normalized[case.permutation] = tuple(out)
    return normalized


def distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def case_sort_key(case: TheoryCase) -> tuple:
    return (
        -case.num_max_edges,
        -case.avg_manhattan,
        case.fixed_points,
        -case.same_row_pairs,
        -case.same_col_pairs,
        tuple(-x for x in case.cycle_partition),
        case.permutation,
    )


def choose_diverse_cases(cases: list[TheoryCase], limit: int) -> list[TheoryCase]:
    if len(cases) <= limit:
        return sorted(cases, key=case_sort_key)

    normalized = normalize_vectors(cases)
    selected = []
    selected_perms = set()

    def add_case(case: TheoryCase) -> None:
        if case.permutation not in selected_perms and len(selected) < limit:
            selected.append(case)
            selected_perms.add(case.permutation)

    dims = len(feature_vector(cases[0]))
    for dim in range(dims):
        add_case(
            sorted(
                cases,
                key=lambda case: (normalized[case.permutation][dim], case_sort_key(case)),
            )[0]
        )
        add_case(
            sorted(
                cases,
                key=lambda case: (-normalized[case.permutation][dim], case_sort_key(case)),
            )[0]
        )

    if not selected:
        add_case(sorted(cases, key=case_sort_key)[0])

    while len(selected) < limit:
        best_case = None
        best_score = None
        for case in cases:
            if case.permutation in selected_perms:
                continue
            vec = normalized[case.permutation]
            min_dist = min(distance(vec, normalized[chosen.permutation]) for chosen in selected)
            score = (
                min_dist,
                case.num_max_edges,
                case.avg_manhattan,
                -case.fixed_points,
                case.same_row_pairs + case.same_col_pairs,
                tuple(-x for x in case.cycle_partition),
                tuple(-x for x in case.permutation),
            )
            if best_score is None or score > best_score:
                best_case = case
                best_score = score
        add_case(best_case)

    return selected


def generate_corner_cases(cases_per_bucket: dict[float, int]) -> dict[float, list[TheoryCase]]:
    buckets = {bucket: [] for bucket in LOAD_BUCKETS}
    for perm in itertools.permutations(NODES):
        case = analyze_permutation(perm)
        bucket = round(case.max_load * 6) / 6.0
        buckets[bucket].append(case)

    selected = {}
    for bucket in LOAD_BUCKETS:
        candidates = buckets[bucket]
        limit = cases_per_bucket.get(bucket, 0)
        if limit <= 0 or not candidates:
            selected[bucket] = []
            continue

        if bucket > 0.0:
            derangements = [case for case in candidates if case.fixed_points == 0]
            if len(derangements) >= limit:
                candidates = derangements

        selected[bucket] = choose_diverse_cases(candidates, limit)

    return selected


def config_text(seed: int, perm: tuple[int, ...], inj_rate: float, num_vcs: int, vc_buf_size: int,
                internal_speedup: float, alloc_iters: int) -> str:
    return f"""num_vcs = {num_vcs};
vc_buf_size = {vc_buf_size};
wait_for_tail_credit = 1;

vc_allocator = islip;
sw_allocator = islip;
alloc_iters = {alloc_iters};

credit_delay = 2;
routing_delay = 0;
vc_alloc_delay = 1;
sw_alloc_delay = 1;
st_final_delay = 1;

input_speedup = 1;
output_speedup = 1;
internal_speedup = {internal_speedup};

sim_type = latency;
warmup_periods = 10;
sample_period = 1000;
max_samples = 20;
latency_thres = 10000.0;
sim_count = 1;
queue_sample_period_cycles = 10;

seed = {seed};
topology = mesh;
k = 3;
n = 2;

routing_function = racke_tree;
packet_size = 1;
traffic = custom_perm;
custom_perm_array = {{{",".join(str(x) for x in perm)}}};
injection_rate = {inj_rate:.10f};
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--booksim", default="src/booksim")
    parser.add_argument("--inj-rate", type=float, default=6.0 / 7.0)
    parser.add_argument("--seeds", default="1,2,3")
    parser.add_argument("--num-vcs", type=int, default=24)
    parser.add_argument("--vc-buf-size", type=int, default=16)
    parser.add_argument("--internal-speedup", type=float, default=2.0)
    parser.add_argument("--alloc-iters", type=int, default=16)
    parser.add_argument("--output", default="")
    parser.add_argument("--cases-7-6", type=int, default=DEFAULT_CASES_PER_BUCKET[7.0 / 6.0])
    parser.add_argument("--cases-1", type=int, default=DEFAULT_CASES_PER_BUCKET[1.0])
    parser.add_argument("--cases-5-6", type=int, default=DEFAULT_CASES_PER_BUCKET[5.0 / 6.0])
    parser.add_argument("--cases-2-3", type=int, default=DEFAULT_CASES_PER_BUCKET[2.0 / 3.0])
    parser.add_argument("--cases-1-2", type=int, default=DEFAULT_CASES_PER_BUCKET[0.5])
    parser.add_argument("--cases-0", type=int, default=DEFAULT_CASES_PER_BUCKET[0.0])
    return parser.parse_args()


def run() -> None:
    args = parse_args()
    booksim = os.path.abspath(args.booksim)
    seeds = [int(token) for token in args.seeds.split(",") if token]
    cases_per_bucket = {
        7.0 / 6.0: args.cases_7_6,
        1.0: args.cases_1,
        5.0 / 6.0: args.cases_5_6,
        2.0 / 3.0: args.cases_2_3,
        0.5: args.cases_1_2,
        0.0: args.cases_0,
    }

    selected = generate_corner_cases(cases_per_bucket)
    ordered_cases = []
    for bucket in LOAD_BUCKETS:
        ordered_cases.extend(selected[bucket])

    total_runs = len(ordered_cases) * len(seeds)
    print(f"Selected {len(ordered_cases)} theory-guided corner cases.")
    print(f"Running {total_runs} BookSim experiments with seeds {seeds}.")

    results = []
    accepted_re = re_compile(r"Accepted packet rate average\s*=\s*([0-9.]+)")
    latency_re = re_compile(r"Packet latency average\s*=\s*([0-9.]+)")
    status_re = re_compile(r"Simulation (converged|unstable)")

    with tempfile.TemporaryDirectory(prefix="racke_corner_perm_", dir="/tmp") as tmpdir:
        case_index = 0
        for bucket in LOAD_BUCKETS:
            for case in selected[bucket]:
                case_index += 1
                for seed in seeds:
                    cfg_path = os.path.join(tmpdir, f"case_{case_index:03d}_seed_{seed}.config")
                    with open(cfg_path, "w", encoding="utf-8") as handle:
                        handle.write(
                            config_text(
                                seed,
                                case.permutation,
                                args.inj_rate,
                                args.num_vcs,
                                args.vc_buf_size,
                                args.internal_speedup,
                                args.alloc_iters,
                            )
                        )
                    proc = subprocess.run(
                        [booksim, cfg_path],
                        capture_output=True,
                        text=True,
                        timeout=1200,
                        check=False,
                    )
                    output = proc.stdout + "\n" + proc.stderr
                    accepted = accepted_re.findall(output)
                    latency = latency_re.findall(output)
                    statuses = status_re.findall(output)
                    results.append(
                        {
                            "bucket": bucket,
                            "theory": asdict(case),
                            "seed": seed,
                            "accepted_rate": float(accepted[-1]) if accepted else None,
                            "latency": float(latency[-1]) if latency else None,
                            "status": statuses[-1] if statuses else "unknown",
                            "returncode": proc.returncode,
                        }
                    )
                print(
                    f"Completed case {case_index:03d}/{len(ordered_cases)} "
                    f"bucket={bucket:.6f} perm={case.permutation}"
                )

    summary = []
    flat_bucket_summary = {}
    for bucket in LOAD_BUCKETS:
        bucket_cases = selected[bucket]
        bucket_results = [item for item in results if abs(item["bucket"] - bucket) <= EPS]
        accepted_values = [item["accepted_rate"] for item in bucket_results if item["accepted_rate"] is not None]
        latency_values = [item["latency"] for item in bucket_results if item["latency"] is not None]
        if accepted_values:
            flat_bucket_summary[str(bucket)] = {
                "count_cases": len(bucket_cases),
                "count_runs": len(bucket_results),
                "mean_accepted_rate": statistics.mean(accepted_values),
                "min_accepted_rate": min(accepted_values),
                "max_accepted_rate": max(accepted_values),
                "mean_latency": statistics.mean(latency_values),
            }
        else:
            flat_bucket_summary[str(bucket)] = {
                "count_cases": len(bucket_cases),
                "count_runs": len(bucket_results),
            }

        if bucket_cases:
            per_case_rows = []
            for case in bucket_cases:
                case_runs = [
                    item
                    for item in bucket_results
                    if tuple(item["theory"]["permutation"]) == case.permutation
                ]
                case_accepted = [item["accepted_rate"] for item in case_runs if item["accepted_rate"] is not None]
                case_latency = [item["latency"] for item in case_runs if item["latency"] is not None]
                per_case_rows.append(
                    {
                        "bucket": bucket,
                        "permutation": case.permutation,
                        "theory_capacity": (1.0 / case.max_load) if case.max_load > 0 else None,
                        "mean_accepted_rate": statistics.mean(case_accepted),
                        "min_accepted_rate": min(case_accepted),
                        "max_accepted_rate": max(case_accepted),
                        "mean_latency": statistics.mean(case_latency),
                        "num_max_edges": case.num_max_edges,
                        "same_row_pairs": case.same_row_pairs,
                        "same_col_pairs": case.same_col_pairs,
                        "cycle_partition": case.cycle_partition,
                    }
                )
            summary.extend(per_case_rows)

    summary.sort(key=lambda row: (row["mean_accepted_rate"], -row["bucket"]))
    payload = {
        "config": {
            "booksim": booksim,
            "inj_rate": args.inj_rate,
            "seeds": seeds,
            "num_vcs": args.num_vcs,
            "vc_buf_size": args.vc_buf_size,
            "internal_speedup": args.internal_speedup,
            "alloc_iters": args.alloc_iters,
            "cases_per_bucket": {str(key): value for key, value in cases_per_bucket.items()},
        },
        "bucket_summary": flat_bucket_summary,
        "worst_cases_by_mean_accepted_rate": summary[:10],
        "selected_cases": {
            str(bucket): [asdict(case) for case in selected[bucket]]
            for bucket in LOAD_BUCKETS
        },
        "results": results,
    }

    if args.output:
        output_path = Path(os.path.abspath(args.output))
        output_dir = output_path.parent
    else:
        output_dir = timestamped_result_dir(
            content="racke_corner_permutations",
            artifact_type="json_results",
            purpose="theory_guided_bucket_scan",
        )
        output_path = output_dir / "racke_corner_perm_results.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    write_readme(
        output_dir,
        title=output_dir.name,
        content="racke corner permutations",
        artifact_type="json results",
        purpose="theory-guided bucket scan for 3x3 mesh permutations",
        notes=[
            f"Primary artifact: {output_path.name}",
            "Generated by tests/scripts/run_racke_corner_permutations.py",
        ],
    )
    print(f"Saved JSON summary to {output_path}")

    print("\nBucket summary:")
    for bucket in LOAD_BUCKETS:
        row = flat_bucket_summary[str(bucket)]
        if "mean_accepted_rate" in row:
            print(
                f"  load={bucket:.6f} cases={row['count_cases']} runs={row['count_runs']} "
                f"mean_acc={row['mean_accepted_rate']:.6f} "
                f"min_acc={row['min_accepted_rate']:.6f} "
                f"max_acc={row['max_accepted_rate']:.6f} "
                f"mean_lat={row['mean_latency']:.2f}"
            )
        else:
            print(f"  load={bucket:.6f} cases={row['count_cases']} runs={row['count_runs']}")

    print("\nLowest accepted-rate cases:")
    for row in summary[:10]:
        print(
            f"  load={row['bucket']:.6f} mean_acc={row['mean_accepted_rate']:.6f} "
            f"perm={row['permutation']} cycle={row['cycle_partition']} "
            f"same_row={row['same_row_pairs']} same_col={row['same_col_pairs']} "
            f"num_max_edges={row['num_max_edges']}"
        )


def re_compile(pattern: str):
    import re

    return re.compile(pattern)


if __name__ == "__main__":
    run()
