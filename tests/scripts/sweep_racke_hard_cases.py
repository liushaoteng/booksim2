#!/usr/bin/env python3

import argparse
import json
import os
import re
import statistics
import subprocess
import tempfile
from pathlib import Path

from artifact_layout import latest_result_artifact, timestamped_result_dir, write_readme


DEFAULT_INJ_RATES = (0.80, 0.82, 0.84, 0.85, 6.0 / 7.0)
DEFAULT_VCS = (24, 30, 36, 48)
DEFAULT_PASS_ACC_MIN = 0.83
DEFAULT_PASS_ACC_MAX = 0.85


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", default="")
    parser.add_argument("--booksim", default="src/booksim")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--inj-rates", default=",".join(f"{rate:.10f}" for rate in DEFAULT_INJ_RATES))
    parser.add_argument("--vc-list", default=",".join(str(vc) for vc in DEFAULT_VCS))
    parser.add_argument("--baseline-inj", type=float, default=6.0 / 7.0)
    parser.add_argument("--baseline-vcs", type=int, default=24)
    parser.add_argument("--vc-buf-size", type=int, default=16)
    parser.add_argument("--internal-speedup", type=float, default=2.0)
    parser.add_argument("--alloc-iters", type=int, default=16)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--pass-acc-min", type=float, default=DEFAULT_PASS_ACC_MIN)
    parser.add_argument("--pass-acc-max", type=float, default=DEFAULT_PASS_ACC_MAX)
    parser.add_argument("--summary-log", default="")
    return parser.parse_args()


def config_text(
    seed: int,
    perm: tuple[int, ...],
    inj_rate: float,
    num_vcs: int,
    vc_buf_size: int,
    internal_speedup: float,
    alloc_iters: int,
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
    statuses = re.findall(r"Simulation (converged|unstable)", output)
    peak_vc = re.findall(r"Overall Max VC Occupancy\s*=\s*(\d+)", output)
    peak_buf = re.findall(r"Overall Max Buffer Occupancy\s*=\s*(\d+)", output)
    return {
        "accepted_rate": float(accepted[-1]) if accepted else None,
        "latency": float(latency[-1]) if latency else None,
        "status": statuses[-1] if statuses else "unknown",
        "peak_occupancy": {
            "vc": int(peak_vc[-1]) if peak_vc else None,
            "buffer": int(peak_buf[-1]) if peak_buf else None,
        },
    }


def run_case(
    booksim: str,
    seed: int,
    perm: tuple[int, ...],
    inj_rate: float,
    num_vcs: int,
    vc_buf_size: int,
    internal_speedup: float,
    alloc_iters: int,
    tmpdir: str,
) -> dict:
    cfg_name = (
        f"perm_{'_'.join(str(x) for x in perm)}"
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


def load_cases(path: str, top_k: int) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["cases"][:top_k]


def summarize_rate_sweep(rows: list[dict], baseline_inj: float) -> dict:
    rows = sorted(rows, key=lambda row: row["injection_rate"])
    baseline = min(rows, key=lambda row: abs(row["injection_rate"] - baseline_inj))
    lower_rows = [row for row in rows if row["injection_rate"] < baseline_inj - 1e-9]
    best_lower = max(
        lower_rows,
        key=lambda row: (
            row["accepted_rate"] if row["accepted_rate"] is not None else -1.0,
            row["efficiency"] if row["efficiency"] is not None else -1.0,
        ),
        default=None,
    )
    peak = max(
        rows,
        key=lambda row: (
            row["accepted_rate"] if row["accepted_rate"] is not None else -1.0,
            row["efficiency"] if row["efficiency"] is not None else -1.0,
        ),
    )
    return {
        "rows": rows,
        "baseline": baseline,
        "best_lower_injection": best_lower,
        "peak_accepted": peak,
        "throughput_rebounds_when_lowering_injection": (
            best_lower is not None
            and baseline["accepted_rate"] is not None
            and best_lower["accepted_rate"] is not None
            and best_lower["accepted_rate"] > baseline["accepted_rate"] + 1e-6
        ),
    }


def summarize_vc_sweep(rows: list[dict], baseline_vcs: int) -> dict:
    rows = sorted(rows, key=lambda row: row["num_vcs"])
    baseline = min(rows, key=lambda row: abs(row["num_vcs"] - baseline_vcs))
    higher_rows = [row for row in rows if row["num_vcs"] > baseline_vcs]
    best_higher = max(
        higher_rows,
        key=lambda row: (
            row["accepted_rate"] if row["accepted_rate"] is not None else -1.0,
            -row["latency"] if row["latency"] is not None else float("-inf"),
        ),
        default=None,
    )
    peak = max(
        rows,
        key=lambda row: (
            row["accepted_rate"] if row["accepted_rate"] is not None else -1.0,
            -row["latency"] if row["latency"] is not None else float("-inf"),
        ),
    )
    return {
        "rows": rows,
        "baseline": baseline,
        "best_higher_vc": best_higher,
        "peak_accepted": peak,
        "throughput_improves_with_more_vcs": (
            best_higher is not None
            and baseline["accepted_rate"] is not None
            and best_higher["accepted_rate"] is not None
            and best_higher["accepted_rate"] > baseline["accepted_rate"] + 1e-6
        ),
    }


def build_summary(case_results: list[dict]) -> dict:
    rate_rebounds = sum(
        1 for case in case_results if case["rate_sweep"]["throughput_rebounds_when_lowering_injection"]
    )
    vc_improvements = sum(
        1 for case in case_results if case["vc_sweep"]["throughput_improves_with_more_vcs"]
    )
    baseline_accepted = [
        case["rate_sweep"]["baseline"]["accepted_rate"]
        for case in case_results
        if case["rate_sweep"]["baseline"]["accepted_rate"] is not None
    ]
    best_lower_accepted = [
        case["rate_sweep"]["best_lower_injection"]["accepted_rate"]
        for case in case_results
        if case["rate_sweep"]["best_lower_injection"] is not None
        and case["rate_sweep"]["best_lower_injection"]["accepted_rate"] is not None
    ]
    best_higher_vc_accepted = [
        case["vc_sweep"]["best_higher_vc"]["accepted_rate"]
        for case in case_results
        if case["vc_sweep"]["best_higher_vc"] is not None
        and case["vc_sweep"]["best_higher_vc"]["accepted_rate"] is not None
    ]
    return {
        "num_cases": len(case_results),
        "rate_rebounds_count": rate_rebounds,
        "vc_improvements_count": vc_improvements,
        "mean_baseline_accepted_rate": statistics.mean(baseline_accepted) if baseline_accepted else None,
        "mean_best_lower_injection_accepted_rate": (
            statistics.mean(best_lower_accepted) if best_lower_accepted else None
        ),
        "mean_best_higher_vc_accepted_rate": (
            statistics.mean(best_higher_vc_accepted) if best_higher_vc_accepted else None
        ),
    }


def run_passes_target_window(row: dict, acc_min: float, acc_max: float) -> bool:
    accepted = row.get("accepted_rate")
    if accepted is None:
        return False
    return acc_min <= accepted <= acc_max


def append_pass_summary_line(
    handle,
    *,
    case_rank: int,
    seed: int,
    sweep_kind: str,
    row: dict,
) -> None:
    peak = row.get("peak_occupancy", {})
    handle.write(
        " | ".join(
            [
                f"case={case_rank}",
                f"sweep={sweep_kind}",
                f"seed={seed}",
                f"num_vcs={row['num_vcs']}",
                f"inj_rate={row['injection_rate']:.6f}",
                f"accepted={row['accepted_rate']:.6f}",
                f"lat_avg={row['latency']:.2f}" if row["latency"] is not None else "lat_avg=NA",
                f"peak_vc={peak.get('vc', 'NA')}",
                f"peak_buf={peak.get('buffer', 'NA')}",
                f"status={row['status']}",
            ]
        )
        + "\n"
    )


def format_sweep_point(row: dict | None, key: str) -> str:
    if row is None:
        return "NA"
    value = row.get(key)
    accepted = row.get("accepted_rate")
    if value is None or accepted is None:
        return "NA"
    if isinstance(value, float):
        return f"{accepted:.6f}@{value:.6f}"
    return f"{accepted:.6f}@{value}"


def choose_case_pass(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            row["accepted_rate"],
            -(row["latency"] if row["latency"] is not None else float("inf")),
            -(row["injection_rate"]),
            -(row["num_vcs"]),
        ),
    )


def main() -> None:
    args = parse_args()
    booksim = os.path.abspath(args.booksim)
    inj_rates = [float(token) for token in args.inj_rates.split(",") if token]
    vc_list = [int(token) for token in args.vc_list.split(",") if token]
    input_json = (
        os.path.abspath(args.input_json)
        if args.input_json
        else str(latest_result_artifact("racke_hard_cases_analysis.json"))
    )
    cases = load_cases(input_json, args.top_k)
    if args.output_json:
        output_json = Path(os.path.abspath(args.output_json))
        result_dir = output_json.parent
    else:
        result_dir = timestamped_result_dir(
            content="racke_hard_cases",
            artifact_type="json_results",
            purpose="inj_and_vc_sweep",
        )
        output_json = result_dir / "racke_hard_sweeps.json"
    summary_log = (
        Path(os.path.abspath(args.summary_log))
        if args.summary_log
        else result_dir / "racke_hard_sweeps_pass.log"
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(os.path.dirname(summary_log), exist_ok=True)

    case_results = []
    with open(summary_log, "w", encoding="utf-8") as summary_handle, tempfile.TemporaryDirectory(prefix="racke_hard_sweeps_", dir="/tmp") as tmpdir:
        summary_handle.write(
            f"# Racke hard-case pass summary, accepted window=[{args.pass_acc_min:.3f}, {args.pass_acc_max:.3f}]\n"
        )
        for case in cases:
            perm = tuple(case["permutation"])
            seed = int(case["worst_seed"])
            passing_rows = []

            rate_rows = []
            for inj_rate in inj_rates:
                row = run_case(
                    booksim,
                    seed,
                    perm,
                    inj_rate,
                    args.baseline_vcs,
                    args.vc_buf_size,
                    args.internal_speedup,
                    args.alloc_iters,
                    tmpdir,
                )
                rate_rows.append(row)
                if run_passes_target_window(row, args.pass_acc_min, args.pass_acc_max):
                    passing_rows.append({"sweep_kind": "inj", **row})

            vc_rows = []
            for num_vcs in vc_list:
                row = run_case(
                    booksim,
                    seed,
                    perm,
                    args.baseline_inj,
                    num_vcs,
                    args.vc_buf_size,
                    args.internal_speedup,
                    args.alloc_iters,
                    tmpdir,
                )
                vc_rows.append(row)
                if run_passes_target_window(row, args.pass_acc_min, args.pass_acc_max):
                    passing_rows.append({"sweep_kind": "vc", **row})

            result = {
                "rank": case["rank"],
                "permutation": perm,
                "cycle_partition": case["cycle_partition"],
                "worst_seed": seed,
                "batch_mean_accepted_rate": case["mean_accepted_rate_from_batch"],
                "baseline_reproduced_accepted_rate": case["reproduced_run"]["accepted_rate"],
                "rate_sweep": summarize_rate_sweep(rate_rows, args.baseline_inj),
                "vc_sweep": summarize_vc_sweep(vc_rows, args.baseline_vcs),
            }
            case_results.append(result)

            best_pass = choose_case_pass(passing_rows)
            if best_pass is not None:
                append_pass_summary_line(
                    summary_handle,
                    case_rank=case["rank"],
                    seed=seed,
                    sweep_kind=best_pass["sweep_kind"],
                    row=best_pass,
                )

            rate_peak = result["rate_sweep"]["peak_accepted"]
            vc_peak = result["vc_sweep"]["peak_accepted"]
            print(
                f"Case {case['rank']} perm={perm} "
                f"baseline_acc={result['rate_sweep']['baseline']['accepted_rate']:.6f} "
                f"best_low_inj={format_sweep_point(result['rate_sweep']['best_lower_injection'], 'injection_rate')} "
                f"best_vc={format_sweep_point(vc_peak, 'num_vcs')}vc "
                f"rate_peak={format_sweep_point(rate_peak, 'injection_rate')}"
            )

    payload = {
        "config": {
            "booksim": booksim,
            "baseline_inj": args.baseline_inj,
            "baseline_vcs": args.baseline_vcs,
            "inj_rates": inj_rates,
            "vc_list": vc_list,
            "vc_buf_size": args.vc_buf_size,
            "internal_speedup": args.internal_speedup,
            "alloc_iters": args.alloc_iters,
            "input_json": input_json,
            "pass_acc_min": args.pass_acc_min,
            "pass_acc_max": args.pass_acc_max,
            "summary_log": str(summary_log),
        },
        "summary": build_summary(case_results),
        "cases": case_results,
    }

    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    write_readme(
        result_dir,
        title=result_dir.name,
        content="racke hard cases",
        artifact_type="sweep results",
        purpose="scan injection-rate and VC-count sensitivity near saturation",
        notes=[
            f"Input summary: {Path(input_json).name}",
            f"Primary JSON: {output_json.name}",
            f"Pass-summary log: {summary_log.name}",
            "Generated by tests/scripts/sweep_racke_hard_cases.py",
        ],
    )
    print(f"Saved sweep results to {output_json}")


if __name__ == "__main__":
    main()
