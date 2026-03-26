#!/usr/bin/env python3

import argparse
import collections
import json
import os
import re
import statistics
import subprocess
import tempfile
from pathlib import Path

from artifact_layout import latest_result_artifact, timestamped_result_dir, write_readme


K = 3
OUTPUTS = 2 * 2 + 1
VOQ_GROUPS_PER_INPUT = OUTPUTS - 1
RACKE_PHASES = 3
REQUIRED_VC_MULTIPLE = VOQ_GROUPS_PER_INPUT * RACKE_PHASES
DEFAULT_INJ_RATES = (0.84, 6.0 / 7.0)
DEFAULT_VCS = (24, 48, 60)
ARCHES = (
    ("vc", 0),
    ("noq_single_output", 1),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", default="")
    parser.add_argument("--booksim", default="src/booksim")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--inj-rates", default=",".join(f"{rate:.10f}" for rate in DEFAULT_INJ_RATES))
    parser.add_argument("--vc-list", default=",".join(str(vc) for vc in DEFAULT_VCS))
    parser.add_argument("--vc-buf-size", type=int, default=16)
    parser.add_argument("--internal-speedup", type=float, default=2.0)
    parser.add_argument("--alloc-iters", type=int, default=16)
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def parse_vc_list(raw: str) -> list[int]:
    vc_list = [int(token) for token in raw.split(",") if token]
    invalid = [num_vcs for num_vcs in vc_list if num_vcs % REQUIRED_VC_MULTIPLE != 0]
    if invalid:
        raise ValueError(
            f"Racke NOQ with no-U-turn VOQ partitioning requires num_vcs divisible by "
            f"{REQUIRED_VC_MULTIPLE}; invalid values: {invalid}"
        )
    return vc_list


def config_text(
    seed: int,
    perm: tuple[int, ...],
    inj_rate: float,
    num_vcs: int,
    vc_buf_size: int,
    internal_speedup: float,
    alloc_iters: int,
    noq: int,
) -> str:
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
noq = {noq};
noq_no_uturn = {1 if noq else 0};

sim_type = latency;
warmup_periods = 10;
sample_period = 1000;
max_samples = 20;
latency_thres = 10000.0;
sim_count = 1;
queue_sample_period_cycles = 0;

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


def parse_run_metrics(output: str) -> dict:
    accepted = re.findall(r"Accepted packet rate average\s*=\s*([0-9.]+)", output)
    latency = re.findall(r"Packet latency average\s*=\s*([0-9.]+)", output)
    status = re.findall(r"Simulation (converged|unstable)", output)
    return {
        "accepted_rate": float(accepted[-1]) if accepted else None,
        "latency": float(latency[-1]) if latency else None,
        "status": status[-1] if status else "unknown",
    }


def voq_layout(num_vcs: int) -> dict:
    injection_vcs_per_output = num_vcs // VOQ_GROUPS_PER_INPUT
    injection_unused = num_vcs - VOQ_GROUPS_PER_INPUT * injection_vcs_per_output
    phase_width = num_vcs // RACKE_PHASES
    phase_unused = num_vcs - RACKE_PHASES * phase_width
    transit_vcs_per_output_phase = phase_width // VOQ_GROUPS_PER_INPUT
    transit_unused_per_phase = phase_width - VOQ_GROUPS_PER_INPUT * transit_vcs_per_output_phase
    return {
        "outputs": OUTPUTS,
        "voq_groups_per_input": VOQ_GROUPS_PER_INPUT,
        "racke_phases": RACKE_PHASES,
        "required_num_vcs_multiple": REQUIRED_VC_MULTIPLE,
        "valid_for_racke_voq_virtual_lanes": (num_vcs % REQUIRED_VC_MULTIPLE == 0),
        "injection_vcs_per_output": injection_vcs_per_output,
        "injection_unused_vcs": injection_unused,
        "transit_phase_width": phase_width,
        "transit_phase_unused_vcs": phase_unused,
        "transit_vcs_per_output_phase": transit_vcs_per_output_phase,
        "transit_unused_vcs_per_phase_after_output_partition": transit_unused_per_phase,
        "total_effectively_partitioned_transit_vcs": (
            RACKE_PHASES * VOQ_GROUPS_PER_INPUT * transit_vcs_per_output_phase
        ),
    }


def load_cases(path: str, top_k: int) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["cases"][:top_k]


def run_case(
    booksim: str,
    seed: int,
    perm: tuple[int, ...],
    inj_rate: float,
    num_vcs: int,
    vc_buf_size: int,
    internal_speedup: float,
    alloc_iters: int,
    arch: str,
    noq: int,
    tmpdir: str,
) -> dict:
    cfg_name = (
        f"{arch}_perm_{'_'.join(str(x) for x in perm)}"
        f"_seed_{seed}_inj_{inj_rate:.6f}_vcs_{num_vcs}.config"
    )
    cfg_path = os.path.join(tmpdir, cfg_name)
    with open(cfg_path, "w", encoding="utf-8") as handle:
        handle.write(
            config_text(
                seed,
                perm,
                inj_rate,
                num_vcs,
                vc_buf_size,
                internal_speedup,
                alloc_iters,
                noq,
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
    metrics = parse_run_metrics(output)
    metrics.update(
        {
            "architecture": arch,
            "noq": noq,
            "seed": seed,
            "permutation": perm,
            "injection_rate": inj_rate,
            "num_vcs": num_vcs,
            "returncode": proc.returncode,
        }
    )
    if metrics["accepted_rate"] is not None:
        metrics["efficiency"] = metrics["accepted_rate"] / inj_rate
    else:
        metrics["efficiency"] = None
    return metrics


def summarize_results(results: list[dict]) -> dict:
    by_key = collections.defaultdict(list)
    for row in results:
        key = (row["architecture"], row["num_vcs"], row["injection_rate"])
        by_key[key].append(row)

    rows = []
    for key, bucket in sorted(by_key.items()):
        accepted = [row["accepted_rate"] for row in bucket if row["accepted_rate"] is not None]
        latency = [row["latency"] for row in bucket if row["latency"] is not None]
        rows.append(
            {
                "architecture": key[0],
                "num_vcs": key[1],
                "injection_rate": key[2],
                "mean_accepted_rate": statistics.mean(accepted) if accepted else None,
                "min_accepted_rate": min(accepted) if accepted else None,
                "max_accepted_rate": max(accepted) if accepted else None,
                "mean_latency": statistics.mean(latency) if latency else None,
                "mean_efficiency": (
                    statistics.mean(row["efficiency"] for row in bucket if row["efficiency"] is not None)
                    if accepted
                    else None
                ),
                "runs": len(bucket),
            }
        )
    return {"aggregate": rows}


def summarize_case_deltas(results: list[dict]) -> list[dict]:
    by_key = collections.defaultdict(dict)
    for row in results:
        key = (tuple(row["permutation"]), row["num_vcs"], row["injection_rate"])
        by_key[key][row["architecture"]] = row

    rows = []
    for key, pair in sorted(by_key.items()):
        if "vc" not in pair or "noq_single_output" not in pair:
            continue
        vc = pair["vc"]
        noq = pair["noq_single_output"]
        rows.append(
            {
                "permutation": key[0],
                "num_vcs": key[1],
                "injection_rate": key[2],
                "vc_accepted_rate": vc["accepted_rate"],
                "noq_accepted_rate": noq["accepted_rate"],
                "accepted_rate_delta_noq_minus_vc": (
                    None
                    if vc["accepted_rate"] is None or noq["accepted_rate"] is None
                    else noq["accepted_rate"] - vc["accepted_rate"]
                ),
                "vc_latency": vc["latency"],
                "noq_latency": noq["latency"],
                "latency_delta_noq_minus_vc": (
                    None
                    if vc["latency"] is None or noq["latency"] is None
                    else noq["latency"] - vc["latency"]
                ),
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    booksim = os.path.abspath(args.booksim)
    inj_rates = [float(token) for token in args.inj_rates.split(",") if token]
    vc_list = parse_vc_list(args.vc_list)
    input_json = (
        os.path.abspath(args.input_json)
        if args.input_json
        else str(latest_result_artifact("racke_hard_cases_analysis.json"))
    )
    cases = load_cases(input_json, args.top_k)

    results = []
    with tempfile.TemporaryDirectory(prefix="racke_voq_vs_vc_", dir="/tmp") as tmpdir:
        for num_vcs in vc_list:
            layout = voq_layout(num_vcs)
            print(
                f"num_vcs={num_vcs} required_multiple={layout['required_num_vcs_multiple']} "
                f"inj_per_output={layout['injection_vcs_per_output']} "
                f"transit_per_output_phase={layout['transit_vcs_per_output_phase']}"
            )
            for case in cases:
                perm = tuple(case["permutation"])
                seed = int(case["worst_seed"])
                for arch, noq in ARCHES:
                    for inj_rate in inj_rates:
                        row = run_case(
                            booksim,
                            seed,
                            perm,
                            inj_rate,
                            num_vcs,
                            args.vc_buf_size,
                            args.internal_speedup,
                            args.alloc_iters,
                            arch,
                            noq,
                            tmpdir,
                        )
                        results.append(row)
                        print(
                            f"case={case['rank']} arch={arch} vcs={num_vcs} "
                            f"inj={inj_rate:.6f} acc={row['accepted_rate']:.6f} "
                            f"lat={row['latency']:.2f}"
                        )

    payload = {
        "config": {
            "booksim": booksim,
            "input_json": os.path.abspath(args.input_json),
            "top_k": args.top_k,
            "inj_rates": inj_rates,
            "vc_list": vc_list,
            "vc_buf_size": args.vc_buf_size,
            "internal_speedup": args.internal_speedup,
            "alloc_iters": args.alloc_iters,
            "queue_model_note": (
                "Current noq path requires routing to commit to a single next output "
                "before queueing; full multi-candidate VOQ selection is not implemented."
            ),
            "architectures": [{"name": arch, "noq": noq} for arch, noq in ARCHES],
        },
        "voq_layout_by_num_vcs": {str(num_vcs): voq_layout(num_vcs) for num_vcs in vc_list},
        "results": results,
        "summary": summarize_results(results),
        "case_deltas": summarize_case_deltas(results),
    }

    if args.output_json:
        output_json = Path(os.path.abspath(args.output_json))
        output_dir = output_json.parent
    else:
        output_dir = timestamped_result_dir(
            content="racke_hard_cases",
            artifact_type="json_results",
            purpose="vc_vs_noq_single_output",
        )
        output_json = output_dir / "racke_voq_vs_vc.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    write_readme(
        output_dir,
        title=output_dir.name,
        content="racke hard cases",
        artifact_type="comparison results",
        purpose="compare baseline VC against single-output NOQ under matched hard cases",
        notes=[
            f"Input summary: {Path(input_json).name}",
            f"Primary artifact: {output_json.name}",
            "Generated by tests/scripts/compare_racke_voq_vs_vc.py",
        ],
    )
    print(f"Saved comparison results to {output_json}")


if __name__ == "__main__":
    main()
