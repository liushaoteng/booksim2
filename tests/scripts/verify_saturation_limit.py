#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from artifact_layout import REPO_ROOT, input_file, timestamped_result_dir, write_readme

RACKE_CONFIG = input_file("configs", "racke_tree_3x3_limit.config")
DSL_CONFIG = input_file("configs", "dsl_3x3.config")
DEFAULT_SEEDS = list(range(101, 131))
DEFAULT_TRAFFICS = ["randperm", "dynamic_perm"]
DEFAULT_RACKE_LIMIT = 0.8571
DEFAULT_DSL_LIMIT = 0.75
DEFAULT_TIMEOUT_S = 1200
DEFAULT_PARAMS = {
    "num_vcs": 48,
    "vc_buf_size": 16,
    "internal_speedup": 2.0,
    "alloc_iters": 16,
}
OVERRIDDEN_CONFIG_KEYS = {
    "injection_rate",
    "perm_seed",
    "traffic",
    "num_vcs",
    "vc_buf_size",
    "internal_speedup",
    "alloc_iters",
}
ALGO_SPECS = {
    "racke": {
        "label": "Racke",
        "config": RACKE_CONFIG,
        "default_rate": DEFAULT_RACKE_LIMIT,
    },
    "dsl": {
        "label": "DSL",
        "config": DSL_CONFIG,
        "default_rate": DEFAULT_DSL_LIMIT,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run RackeTree/DSL saturation-limit checks with reproducible configs."
    )
    parser.add_argument(
        "--booksim",
        default=str(REPO_ROOT / "src" / "booksim"),
        help="Path to the BookSim binary. Defaults to src/booksim under the repo root.",
    )
    parser.add_argument(
        "--algos",
        nargs="+",
        choices=sorted(ALGO_SPECS),
        default=list(ALGO_SPECS),
        help="Algorithms to run.",
    )
    parser.add_argument(
        "--traffics",
        nargs="+",
        default=DEFAULT_TRAFFICS,
        help="Traffic patterns to run.",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=DEFAULT_SEEDS,
        help="Permutation seeds to run.",
    )
    parser.add_argument(
        "--racke-rate",
        type=float,
        default=DEFAULT_RACKE_LIMIT,
        help="Injection rate used for RackeTree runs.",
    )
    parser.add_argument(
        "--dsl-rate",
        type=float,
        default=DEFAULT_DSL_LIMIT,
        help="Injection rate used for DSL runs.",
    )
    parser.add_argument(
        "--num-vcs",
        type=int,
        default=DEFAULT_PARAMS["num_vcs"],
        help="num_vcs override written into each generated config.",
    )
    parser.add_argument(
        "--vc-buf-size",
        type=int,
        default=DEFAULT_PARAMS["vc_buf_size"],
        help="vc_buf_size override written into each generated config.",
    )
    parser.add_argument(
        "--internal-speedup",
        type=float,
        default=DEFAULT_PARAMS["internal_speedup"],
        help="internal_speedup override written into each generated config.",
    )
    parser.add_argument(
        "--alloc-iters",
        type=int,
        default=DEFAULT_PARAMS["alloc_iters"],
        help="alloc_iters override written into each generated config.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_S,
        help="Per-run timeout in seconds.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional explicit result directory. If omitted, a timestamped folder is created under tests/data/results/.",
    )
    return parser.parse_args()


def resolve_rate(algo_key: str, args: argparse.Namespace) -> float:
    if algo_key == "racke":
        return args.racke_rate
    if algo_key == "dsl":
        return args.dsl_rate
    raise ValueError(f"Unsupported algorithm key: {algo_key}")


def ensure_booksim(booksim_path: Path) -> Path:
    booksim_path = booksim_path.resolve()
    if not booksim_path.exists():
        raise FileNotFoundError(
            f"BookSim binary not found at {booksim_path}. Build it first with `make -C src`."
        )
    return booksim_path


def make_result_dir(output_dir: Path | None) -> Path:
    if output_dir is not None:
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    return timestamped_result_dir(
        content="racke_dsl_limit_verification",
        artifact_type="seed_runs",
        purpose="latency_limit_scan",
    )


def generate_config(config_base: Path, config_path: Path, rate: float, seed: int, traffic: str, **kwargs: float) -> None:
    if not config_base.exists():
        raise FileNotFoundError(f"Base config {config_base} not found.")

    lines = config_base.read_text(encoding="utf-8").splitlines(keepends=True)
    with config_path.open("w", encoding="utf-8") as handle:
        for line in lines:
            clean = line.strip()
            if not clean or clean.startswith("//"):
                handle.write(line)
                continue
            key_match = re.match(r"^\s*([a-zA-Z0-9_]+)\s*=", clean)
            if key_match and key_match.group(1) in OVERRIDDEN_CONFIG_KEYS:
                continue
            handle.write(line)

        handle.write(f"injection_rate = {rate};\n")
        handle.write(f"perm_seed = {seed};\n")
        handle.write(f"traffic = {traffic};\n")
        for key, value in kwargs.items():
            handle.write(f"{key} = {value};\n")


def run_point(
    *,
    algo: str,
    booksim_path: Path,
    config_base: Path,
    runs_dir: Path,
    rate: float,
    seed: int,
    traffic: str,
    timeout_s: int,
    **kwargs: float,
) -> dict[str, object] | None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{algo}_s{seed}_{traffic}_{timestamp}"
    config_path = runs_dir / f"{prefix}.config"
    log_path = runs_dir / f"{prefix}.log"
    json_path = runs_dir / f"{prefix}.json"

    generate_config(config_base, config_path, rate, seed, traffic, **kwargs)
    print(f"  Running {algo} {traffic} seed {seed} @ {rate}...", end="", flush=True)

    try:
        result = subprocess.run(
            [str(booksim_path), str(config_path)],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=REPO_ROOT,
        )
        output = result.stdout + "\n" + result.stderr
        log_path.write_text(output, encoding="utf-8")

        if result.returncode != 0:
            print(f" failed (exit {result.returncode}).")
            return None

        accepted = re.search(r"Accepted (?:packet|flit) rate average\s*=\s*([\d\.]+)", output)
        lat_avg = re.search(r"Packet latency average\s*=\s*([\d\.]+)", output)
        lat_min = re.search(r"minimum\s*=\s*([\d\.]+)", output)
        lat_max = re.search(r"maximum\s*=\s*([\d\.]+)", output)
        percentiles = {
            f"p{p}": float(val)
            for p, val in re.findall(r"(\d+)th percentile\s*=\s*([\d\.]+)", output)
        }
        peak_vc = re.search(r"Overall Max VC Occupancy = (\d+)", output)
        peak_buf = re.search(r"Overall Max Buffer Occupancy = (\d+)", output)
        queue_avg = re.search(r"Overall Sampled Queue Average = ([\d\.]+)", output)
        queue_max = re.search(r"Overall Sampled Queue Max = ([\d\.]+)", output)

        success = (
            result.returncode == 0
            and accepted is not None
            and lat_avg is not None
            and "Simulation unstable" not in output
        )

        stats: dict[str, object] = {
            "algo": algo,
            "seed": seed,
            "traffic": traffic,
            "rate": rate,
            "config": str(config_path),
            "log": str(log_path),
            "timestamp": timestamp,
            "success": success,
            "accepted_rate": float(accepted.group(1)) if accepted else 0.0,
            "latency": {
                "average": float(lat_avg.group(1)) if lat_avg else 0.0,
                "min": float(lat_min.group(1)) if lat_min else 0.0,
                "max": float(lat_max.group(1)) if lat_max else 0.0,
                "percentiles": percentiles,
            },
            "peak_occupancy": {
                "vc": int(peak_vc.group(1)) if peak_vc else 0,
                "buffer": int(peak_buf.group(1)) if peak_buf else 0,
            },
            "sampled_queue_avg": float(queue_avg.group(1)) if queue_avg else 0.0,
            "sampled_queue_max": float(queue_max.group(1)) if queue_max else 0.0,
        }
        json_path.write_text(json.dumps(stats, indent=4) + "\n", encoding="utf-8")
        print(f" done. accepted={stats['accepted_rate']:.4f}")
        return stats
    except subprocess.TimeoutExpired:
        print(" timeout.")
        return None
    except Exception as exc:
        print(f" parse error: {exc}")
        return None


def write_summary(summary_path: Path, stats_list: list[dict[str, object]]) -> None:
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write(f"BookSim Verification Summary - {datetime.now()}\n")
        handle.write("-" * 120 + "\n")
        handle.write(
            f"{'Algo':<8} | {'Traffic':<12} | {'Seed':<5} | {'Accepted':<10} | {'LatAvg':<10} | {'PeakVC':<8} | {'PeakBuf':<8} | {'Status':<10}\n"
        )
        handle.write("-" * 120 + "\n")
        for stats in stats_list:
            status = "OK" if stats["success"] else "UNSTABLE"
            latency = stats["latency"]
            peak = stats["peak_occupancy"]
            handle.write(
                f"{stats['algo']:<8} | {stats['traffic']:<12} | {stats['seed']:<5} | "
                f"{stats['accepted_rate']:<10.4f} | {latency['average']:<10.2f} | "
                f"{peak['vc']:<8} | {peak['buffer']:<8} | {status:<10}\n"
            )


def main() -> int:
    args = parse_args()
    booksim_path = ensure_booksim(Path(args.booksim))
    result_dir = make_result_dir(args.output_dir)
    runs_dir = result_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    write_readme(
        result_dir,
        title=result_dir.name,
        content="racke and dsl limit verification",
        artifact_type="seed runs",
        purpose="verify accepted throughput and latency near configured limit points",
        notes=[
            f"Primary raw runs directory: {runs_dir.name}/",
            "Generated by tests/scripts/verify_saturation_limit.py",
        ],
    )
    write_readme(
        runs_dir,
        title=runs_dir.name,
        content="per-seed verification runs",
        artifact_type="raw config, log, and json files",
        purpose="store individual Racke/DSL verification runs",
        notes=["Generated by tests/scripts/verify_saturation_limit.py"],
    )

    params = {
        "num_vcs": args.num_vcs,
        "vc_buf_size": args.vc_buf_size,
        "internal_speedup": args.internal_speedup,
        "alloc_iters": args.alloc_iters,
    }
    selected = [ALGO_SPECS[key] | {"key": key, "rate": resolve_rate(key, args)} for key in args.algos]
    all_stats: list[dict[str, object]] = []

    print(f"Starting verification in {runs_dir}")
    print(f"Using BookSim binary: {booksim_path}")
    for traffic in args.traffics:
        print(f"\nEvaluating traffic: {traffic}")
        for seed in args.seeds:
            for spec in selected:
                stats = run_point(
                    algo=spec["label"],
                    booksim_path=booksim_path,
                    config_base=Path(spec["config"]),
                    runs_dir=runs_dir,
                    rate=spec["rate"],
                    seed=seed,
                    traffic=traffic,
                    timeout_s=args.timeout,
                    **params,
                )
                if stats:
                    all_stats.append(stats)

    summary_path = result_dir / "verification_summary.log"
    write_summary(summary_path, all_stats)
    print(f"\nVerification complete. Results in {runs_dir}")
    print(f"Summary log: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
