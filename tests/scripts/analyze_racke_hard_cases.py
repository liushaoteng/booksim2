#!/usr/bin/env python3

import argparse
import collections
import json
import os
import re
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path

from artifact_layout import latest_result_artifact, timestamped_result_dir, write_readme


K = 3
NODES = tuple(range(K * K))
PHASE_NAMES = {0: "phase0_scatter", 1: "phase1_middle", 2: "phase2_final"}
INPUT_PORT_NAMES = {
    0: "from_pos_x",
    1: "from_neg_x",
    2: "from_pos_y",
    3: "from_neg_y",
    4: "inject",
}


@dataclass(frozen=True)
class QueueEntry:
    node: int
    port: int
    vc: int
    max_occ: int
    min_occ: int
    avg_occ: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", default="")
    parser.add_argument("--booksim", default="src/booksim")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--log-dir", default="")
    return parser.parse_args()


def config_text(seed: int, perm: tuple[int, ...]) -> str:
    return f"""num_vcs = 24;
vc_buf_size = 16;
wait_for_tail_credit = 1;

vc_allocator = islip;
sw_allocator = islip;
alloc_iters = 16;

credit_delay = 2;
routing_delay = 0;
vc_alloc_delay = 1;
sw_alloc_delay = 1;
st_final_delay = 1;

input_speedup = 1;
output_speedup = 1;
internal_speedup = 2.0;

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
injection_rate = {6.0 / 7.0:.10f};
"""


def path_xy(u: int, v: int) -> list[tuple[int, int]]:
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
    for edge in path_xy(u, v):
        edges[tuple(sorted(edge))] += weight


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


def permutation_edge_loads(perm: tuple[int, ...]) -> dict[tuple[int, int], float]:
    edge_counts = collections.defaultdict(float)
    for u, v in enumerate(perm):
        if u == v:
            continue
        for edge, load in PAIR_CONTRIBUTIONS[(u, v)].items():
            edge_counts[edge] += load
    return dict(edge_counts)


def neighbor_port(node: int, neighbor: int) -> int:
    x0, y0 = node % K, node // K
    x1, y1 = neighbor % K, neighbor // K
    dx = x1 - x0
    dy = y1 - y0
    if dx == 1 and dy == 0:
        return 0
    if dx == -1 and dy == 0:
        return 1
    if dx == 0 and dy == 1:
        return 2
    if dx == 0 and dy == -1:
        return 3
    raise ValueError((node, neighbor))


def edge_to_input_ports(edge: tuple[int, int]) -> list[tuple[int, int]]:
    u, v = edge
    return [(u, neighbor_port(u, v)), (v, neighbor_port(v, u))]


def select_hardest_cases(payload: dict, top_k: int) -> list[dict]:
    grouped = {}
    for row in payload["results"]:
        if abs(row["bucket"] - (7.0 / 6.0)) > 1e-9:
            continue
        perm = tuple(row["theory"]["permutation"])
        entry = grouped.setdefault(
            perm,
            {
                "theory": row["theory"],
                "runs": [],
            },
        )
        entry["runs"].append(row)

    cases = []
    for perm, entry in grouped.items():
        mean_acc = statistics.mean(run["accepted_rate"] for run in entry["runs"])
        worst_run = min(entry["runs"], key=lambda run: run["accepted_rate"])
        cases.append(
            {
                "permutation": perm,
                "theory": entry["theory"],
                "mean_accepted_rate": mean_acc,
                "worst_seed": worst_run["seed"],
                "worst_seed_accepted_rate": worst_run["accepted_rate"],
                "worst_seed_latency": worst_run["latency"],
            }
        )

    cases.sort(key=lambda case: case["mean_accepted_rate"])
    return cases[:top_k]


def parse_queue_blocks(output: str) -> list[list[QueueEntry]]:
    blocks = []
    current = None
    line_re = re.compile(
        r"Node (\d+) Port (\d+) VC (\d+) -> max: (\d+), min: (\d+), avg: ([0-9.]+)"
    )

    for line in output.splitlines():
        if line.startswith("====== Queue Sample Statistics"):
            current = []
            blocks.append(current)
            continue
        if line.startswith("====== Peak Queue Occupancy Statistics"):
            current = None
            continue
        if current is None:
            continue
        match = line_re.search(line)
        if match:
            current.append(
                QueueEntry(
                    node=int(match.group(1)),
                    port=int(match.group(2)),
                    vc=int(match.group(3)),
                    max_occ=int(match.group(4)),
                    min_occ=int(match.group(5)),
                    avg_occ=float(match.group(6)),
                )
            )
    return blocks


def summarize_blocks(blocks: list[list[QueueEntry]], num_vcs: int) -> dict:
    vcs_per_phase = num_vcs // 3

    phase_totals = collections.defaultdict(list)
    phase_port_totals = collections.defaultdict(list)
    node_port_phase_totals = collections.defaultdict(list)
    vc_totals = collections.defaultdict(list)
    node_port_totals = collections.defaultdict(list)

    for block in blocks:
        per_phase = collections.defaultdict(float)
        per_phase_port = collections.defaultdict(float)
        per_node_port_phase = collections.defaultdict(float)
        per_vc = collections.defaultdict(float)
        per_node_port = collections.defaultdict(float)

        for entry in block:
            phase = entry.vc // vcs_per_phase
            key_phase_port = (phase, entry.port)
            key_node_port_phase = (entry.node, entry.port, phase)
            key_vc = (entry.node, entry.port, entry.vc)
            key_node_port = (entry.node, entry.port)

            per_phase[phase] += entry.avg_occ
            per_phase_port[key_phase_port] += entry.avg_occ
            per_node_port_phase[key_node_port_phase] += entry.avg_occ
            per_vc[key_vc] += entry.avg_occ
            per_node_port[key_node_port] += entry.avg_occ

        for key, value in per_phase.items():
            phase_totals[key].append(value)
        for key, value in per_phase_port.items():
            phase_port_totals[key].append(value)
        for key, value in per_node_port_phase.items():
            node_port_phase_totals[key].append(value)
        for key, value in per_vc.items():
            vc_totals[key].append(value)
        for key, value in per_node_port.items():
            node_port_totals[key].append(value)

    def summarize_map(source: dict, formatter):
        rows = []
        for key, values in source.items():
            rows.append(
                {
                    **formatter(key),
                    "mean_window_avg_occ": statistics.mean(values),
                    "max_window_avg_occ": max(values),
                }
            )
        rows.sort(key=lambda row: (row["mean_window_avg_occ"], row["max_window_avg_occ"]), reverse=True)
        return rows

    return {
        "num_blocks": len(blocks),
        "phase_summary": summarize_map(
            phase_totals,
            lambda key: {"phase": key, "phase_name": PHASE_NAMES[key]},
        ),
        "phase_port_summary": summarize_map(
            phase_port_totals,
            lambda key: {
                "phase": key[0],
                "phase_name": PHASE_NAMES[key[0]],
                "port": key[1],
                "port_name": INPUT_PORT_NAMES[key[1]],
            },
        ),
        "node_port_phase_summary": summarize_map(
            node_port_phase_totals,
            lambda key: {
                "node": key[0],
                "port": key[1],
                "port_name": INPUT_PORT_NAMES[key[1]],
                "phase": key[2],
                "phase_name": PHASE_NAMES[key[2]],
            },
        ),
        "node_port_summary": summarize_map(
            node_port_totals,
            lambda key: {
                "node": key[0],
                "port": key[1],
                "port_name": INPUT_PORT_NAMES[key[1]],
            },
        ),
        "vc_summary": summarize_map(
            vc_totals,
            lambda key: {
                "node": key[0],
                "port": key[1],
                "port_name": INPUT_PORT_NAMES[key[1]],
                "vc": key[2],
                "phase": key[2] // vcs_per_phase,
                "phase_name": PHASE_NAMES[key[2] // vcs_per_phase],
            },
        ),
    }


def parse_run_metrics(output: str) -> dict:
    accepted = re.findall(r"Accepted packet rate average\s*=\s*([0-9.]+)", output)
    latency = re.findall(r"Packet latency average\s*=\s*([0-9.]+)", output)
    peak_vc = re.findall(r"Overall Max VC Occupancy = (\d+)", output)
    peak_buf = re.findall(r"Overall Max Buffer Occupancy = (\d+)", output)
    return {
        "accepted_rate": float(accepted[-1]) if accepted else None,
        "latency": float(latency[-1]) if latency else None,
        "overall_max_vc_occupancy": int(peak_vc[-1]) if peak_vc else None,
        "overall_max_buffer_occupancy": int(peak_buf[-1]) if peak_buf else None,
    }


def root_cause_notes(queue_summary: dict, critical_ports: set[tuple[int, int]]) -> list[str]:
    notes = []
    phase_summary = queue_summary["phase_summary"]
    phase_port_summary = queue_summary["phase_port_summary"]
    node_port_phase_summary = queue_summary["node_port_phase_summary"]
    node_port_summary = queue_summary["node_port_summary"]

    if phase_summary:
        dominant_phase = phase_summary[0]
        notes.append(
            f"Dominant queue mass sits in {dominant_phase['phase_name']} "
            f"(mean window avg occupancy {dominant_phase['mean_window_avg_occ']:.2f})."
        )

    injection_rows = [row for row in phase_port_summary if row["port"] == 4]
    if injection_rows:
        hot_injection = injection_rows[0]
        notes.append(
            f"Local injection queues remain active, with the hottest injection slice in "
            f"{hot_injection['phase_name']} at mean window avg occupancy "
            f"{hot_injection['mean_window_avg_occ']:.2f}."
        )

    critical_rows = [
        row
        for row in node_port_summary
        if (row["node"], row["port"]) in critical_ports
    ]
    if critical_rows:
        critical_rows.sort(key=lambda row: row["mean_window_avg_occ"], reverse=True)
        top = critical_rows[0]
        notes.append(
            f"The hottest transit queue aligns with a theory-critical edge endpoint at "
            f"node {top['node']} {top['port_name']} (mean window avg occupancy "
            f"{top['mean_window_avg_occ']:.2f})."
        )

    if node_port_phase_summary:
        hottest = node_port_phase_summary[0]
        notes.append(
            f"The single hottest node/port/phase bucket is node {hottest['node']} "
            f"{hottest['port_name']} in {hottest['phase_name']} "
            f"(mean window avg occupancy {hottest['mean_window_avg_occ']:.2f})."
        )

    return notes


def main() -> None:
    args = parse_args()
    input_json = (
        Path(os.path.abspath(args.input_json))
        if args.input_json
        else latest_result_artifact("racke_corner_perm_results.json")
    )
    with open(input_json, encoding="utf-8") as handle:
        payload = json.load(handle)

    hardest = select_hardest_cases(payload, args.top_k)
    booksim = os.path.abspath(args.booksim)
    if args.output_json:
        output_json = Path(os.path.abspath(args.output_json))
        result_dir = output_json.parent
    else:
        result_dir = timestamped_result_dir(
            content="racke_hard_cases",
            artifact_type="replay_logs",
            purpose="worst_seed_queue_analysis",
        )
        output_json = result_dir / "racke_hard_cases_analysis.json"

    output_md = (
        Path(os.path.abspath(args.output_md))
        if args.output_md
        else result_dir / "racke_hard_cases_analysis.md"
    )
    log_dir = (
        Path(os.path.abspath(args.log_dir))
        if args.log_dir
        else result_dir / "hard_case_logs"
    )

    result_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    analysis = []
    for rank, case in enumerate(hardest, start=1):
        perm = tuple(case["permutation"])
        seed = case["worst_seed"]
        cfg_text = config_text(seed, perm)
        cfg_path = log_dir / f"hard_case_{rank:02d}.config"
        log_path = log_dir / f"hard_case_{rank:02d}.log"
        with open(cfg_path, "w", encoding="utf-8") as handle:
            handle.write(cfg_text)

        proc = subprocess.run(
            [booksim, cfg_path],
            capture_output=True,
            text=True,
            timeout=1200,
            check=False,
        )
        output = proc.stdout + "\n" + proc.stderr
        with open(log_path, "w", encoding="utf-8") as handle:
            handle.write(output)

        metrics = parse_run_metrics(output)
        queue_blocks = parse_queue_blocks(output)
        queue_summary = summarize_blocks(queue_blocks, 24)

        edge_loads = permutation_edge_loads(perm)
        max_load = max(edge_loads.values()) if edge_loads else 0.0
        max_edges = sorted(
            edge for edge, load in edge_loads.items() if abs(load - max_load) <= 1e-9
        )
        critical_ports = set()
        for edge in max_edges:
            critical_ports.update(edge_to_input_ports(edge))

        analysis.append(
            {
                "rank": rank,
                "permutation": perm,
                "cycle_partition": tuple(case["theory"]["cycle_partition"]),
                "num_max_edges": case["theory"]["num_max_edges"],
                "same_row_pairs": case["theory"]["same_row_pairs"],
                "same_col_pairs": case["theory"]["same_col_pairs"],
                "mean_accepted_rate_from_batch": case["mean_accepted_rate"],
                "worst_seed": seed,
                "worst_seed_accepted_rate_from_batch": case["worst_seed_accepted_rate"],
                "reproduced_run": metrics,
                "critical_edges": max_edges,
                "critical_input_ports": sorted(critical_ports),
                "queue_summary": {
                    "num_blocks": queue_summary["num_blocks"],
                    "phase_summary_top3": queue_summary["phase_summary"][:3],
                    "phase_port_summary_top8": queue_summary["phase_port_summary"][:8],
                    "node_port_phase_summary_top8": queue_summary["node_port_phase_summary"][:8],
                    "node_port_summary_top8": queue_summary["node_port_summary"][:8],
                    "vc_summary_top12": queue_summary["vc_summary"][:12],
                },
                "root_cause_notes": root_cause_notes(queue_summary, critical_ports),
                "config_path": str(cfg_path),
                "log_path": str(log_path),
            }
        )

    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump({"cases": analysis}, handle, indent=2)

    with open(output_md, "w", encoding="utf-8") as handle:
        handle.write("# Racke Hard Cases Queue/VC/Phase Analysis\n\n")
        handle.write(
            "This report reruns the hardest theory-7/6 permutations from "
            f"`{input_json}` using their worst observed seed, "
            "then aggregates queue samples by phase, port, and VC.\n\n"
        )
        for case in analysis:
            handle.write(f"## Case {case['rank']}\n\n")
            handle.write(f"- Permutation: `{case['permutation']}`\n")
            handle.write(f"- Cycle partition: `{case['cycle_partition']}`\n")
            handle.write(f"- Theory max-load edges: `{case['num_max_edges']}` edges at `7/6`\n")
            handle.write(
                f"- Batch mean accepted rate: `{case['mean_accepted_rate_from_batch']:.6f}`\n"
            )
            handle.write(
                f"- Worst seed replay: `seed={case['worst_seed']}`, "
                f"`accepted={case['reproduced_run']['accepted_rate']:.6f}`, "
                f"`latency={case['reproduced_run']['latency']:.2f}`\n"
            )
            handle.write(f"- Critical edges: `{case['critical_edges']}`\n")
            handle.write(f"- Log: `{case['log_path']}`\n\n")
            handle.write("Top phase buckets:\n\n")
            for row in case["queue_summary"]["phase_summary_top3"]:
                handle.write(
                    f"- {row['phase_name']}: mean window avg occupancy "
                    f"`{row['mean_window_avg_occ']:.2f}`, peak "
                    f"`{row['max_window_avg_occ']:.2f}`\n"
                )
            handle.write("\nTop node/port/phase buckets:\n\n")
            for row in case["queue_summary"]["node_port_phase_summary_top8"][:5]:
                handle.write(
                    f"- Node `{row['node']}` `{row['port_name']}` `{row['phase_name']}`: "
                    f"mean `{row['mean_window_avg_occ']:.2f}`, peak `{row['max_window_avg_occ']:.2f}`\n"
                )
            handle.write("\nTop VC hotspots:\n\n")
            for row in case["queue_summary"]["vc_summary_top12"][:5]:
                handle.write(
                    f"- Node `{row['node']}` `{row['port_name']}` VC `{row['vc']}` "
                    f"({row['phase_name']}): mean `{row['mean_window_avg_occ']:.2f}`, "
                    f"peak `{row['max_window_avg_occ']:.2f}`\n"
                )
            handle.write("\nNotes:\n\n")
            for note in case["root_cause_notes"]:
                handle.write(f"- {note}\n")
            handle.write("\n")

    write_readme(
        result_dir,
        title=result_dir.name,
        content="racke hard cases",
        artifact_type="replay logs and analysis",
        purpose="replay worst-seed hard cases and summarize queue, phase, and VC hotspots",
        notes=[
            f"Input summary: {input_json.name}",
            f"Primary JSON: {output_json.name}",
            f"Primary report: {output_md.name}",
            f"Per-case logs directory: {log_dir.name}/",
            "Generated by tests/scripts/analyze_racke_hard_cases.py",
        ],
    )
    write_readme(
        log_dir,
        title=log_dir.name,
        content="per-case racke hard-case logs",
        artifact_type="raw config and log files",
        purpose="preserve reproduced worst-seed configs and BookSim console output",
        notes=[
            "Contains hard_case_XX.config and hard_case_XX.log pairs.",
            "Generated by tests/scripts/analyze_racke_hard_cases.py",
        ],
    )

    print(f"Saved JSON analysis to {output_json}")
    print(f"Saved Markdown report to {output_md}")
    for case in analysis:
        print(
            f"Case {case['rank']} accepted={case['reproduced_run']['accepted_rate']:.6f} "
            f"perm={case['permutation']}"
        )


if __name__ == "__main__":
    main()
