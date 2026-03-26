import os
import re
import json
import subprocess
from datetime import datetime
from pathlib import Path

from artifact_layout import input_file, timestamped_result_dir, write_readme

# Configuration
RACKE_CONFIG = input_file("configs", "racke_tree_3x3_limit.config")
DSL_CONFIG = input_file("configs", "dsl_3x3.config")
SEEDS = list(range(101, 131)) # 30 seeds
RACKE_LIMIT = 0.8571
DSL_LIMIT = 0.75

def run_point(algo, config_base, runs_dir, rate, seed, traffic="randperm", **kwargs):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{algo}_s{seed}_{traffic}_{timestamp}"
    
    if not os.path.exists(runs_dir):
        os.makedirs(runs_dir)
        
    config_path = os.path.join(runs_dir, f"{prefix}.config")
    log_path = os.path.join(runs_dir, f"{prefix}.log")
    json_path = os.path.join(runs_dir, f"{prefix}.json")
    
    # Generate config
    if not os.path.exists(config_base):
        print(f" Error: Base config {config_base} not found.")
        return None
        
    with open(config_base, "r") as f:
        lines = f.readlines()
    
    with open(config_path, "w") as f:
        for line in lines:
            clean = line.strip()
            if not clean or clean.startswith("//"):
                f.write(line)
                continue
            key_match = re.match(r'^\s*([a-zA-Z0-9_]+)\s*=', clean)
            if key_match:
                key = key_match.group(1)
                if key in ["injection_rate", "perm_seed", "traffic", "num_vcs", "vc_buf_size", "internal_speedup"]:
                    continue
            f.write(line)
            
        f.write(f"injection_rate = {rate};\n")
        f.write(f"perm_seed = {seed};\n")
        f.write(f"traffic = {traffic};\n")
        for k, v in kwargs.items():
            f.write(f"{k} = {v};\n")

    print(f"  Running {algo} {traffic} Seed {seed} @ {rate}...", end="", flush=True)
    
    try:
        cmd = ["../../src/booksim", config_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
        output = result.stdout + "\n" + result.stderr
        
        with open(log_path, "w") as f:
            f.write(output)
            
        if result.returncode != 0:
            print(f" Failed (Code {result.returncode}).")
            return None
            
        stats = {
            "algo": algo,
            "seed": seed,
            "traffic": traffic,
            "rate": rate,
            "config": config_path,
            "timestamp": timestamp,
            "success": "Simulation converged" in output
        }
        
        # Accepted Rate - allow for optional space before/after '='
        # Accepted packet rate average = 0.853722 (1 samples)
        acc_match = re.search(r'Accepted (?:packet|flit) rate average\s*=\s*([\d\.]+)', output)
        stats["accepted_rate"] = float(acc_match.group(1)) if acc_match else 0.0
        
        # Latency
        lat_avg = re.search(r'Packet latency average\s*=\s*([\d\.]+)', output)
        lat_min = re.search(r'minimum\s*=\s*([\d\.]+)', output)
        lat_max = re.search(r'maximum\s*=\s*([\d\.]+)', output)
        
        # Percentiles
        perc_matches = re.findall(r'(\d+)th percentile\s*=\s*([\d\.]+)', output)
        percentiles = {f"p{p}": float(val) for p, val in perc_matches}
        
        stats["latency"] = {
            "average": float(lat_avg.group(1)) if lat_avg else 0.0,
            "min": float(lat_min.group(1)) if lat_min else 0.0,
            "max": float(lat_max.group(1)) if lat_max else 0.0,
            "percentiles": percentiles
        }
        
        # Peak Occupancy
        peak_vc = re.search(r'Overall Max VC Occupancy = (\d+)', output)
        peak_buf = re.search(r'Overall Max Buffer Occupancy = (\d+)', output)
        stats["peak_occupancy"] = {
            "vc": int(peak_vc.group(1)) if peak_vc else 0,
            "buffer": int(peak_buf.group(1)) if peak_buf else 0
        }
        
        # Sampled Queue
        s_avg = re.search(r'Overall Sampled Queue Average = ([\d\.]+)', output)
        s_max = re.search(r'Overall Sampled Queue Max = ([\d\.]+)', output)
        stats["sampled_queue_avg"] = float(s_avg.group(1)) if s_avg else 0.0
        stats["sampled_queue_max"] = float(s_max.group(1)) if s_max else 0.0
        
        with open(json_path, "w") as f:
            json.dump(stats, f, indent=4)
            
        print(f" Done. Rate: {stats['accepted_rate']:.4f}")
        return stats
    except subprocess.TimeoutExpired:
        print(" Timeout.")
        return None
    except Exception as e:
        print(f" Parse Error: {e}")
        return None

def main():
    result_dir = timestamped_result_dir(
        content="racke_dsl_limit_verification",
        artifact_type="seed_runs",
        purpose="latency_limit_scan",
    )
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
        "num_vcs": 48,
        "vc_buf_size": 16,
        "internal_speedup": 2.0,
        "alloc_iters": 16
    }
    
    all_stats = []
    
    print(f"Starting Final Verification in {runs_dir}")
    for traffic in ["randperm", "dynamic_perm"]:
        print(f"\nEvaluating Traffic: {traffic}")
        for seed in SEEDS:
            # Racke
            s = run_point("Racke", str(RACKE_CONFIG), str(runs_dir), RACKE_LIMIT, seed, traffic=traffic, **params)
            if s: all_stats.append(s)
            
            # DSL
            # s = run_point("DSL", str(DSL_CONFIG), str(runs_dir), DSL_LIMIT, seed, traffic=traffic, **params)
            # if s: all_stats.append(s)

    # Final summary log
    summary_path = result_dir / "verification_summary.log"
    with open(summary_path, "w") as f:
        f.write(f"BookSim Final Verification Summary - {datetime.now()}\n")
        f.write("-" * 120 + "\n")
        f.write(f"{'Algo':<8} | {'Traffic':<12} | {'Seed':<5} | {'Accepted':<10} | {'LatAvg':<10} | {'PeakVC':<8} | {'PeakBuf':<8} | {'Status':<10}\n")
        f.write("-" * 120 + "\n")
        for s in all_stats:
            status = "OK" if s['success'] else "UNSTABLE"
            f.write(f"{s['algo']:<8} | {s['traffic']:<12} | {s['seed']:<5} | {s['accepted_rate']:<10.4f} | {s['latency']['average']:<10.2f} | {s['peak_occupancy']['vc']:<8} | {s['peak_occupancy']['buffer']:<8} | {status:<10}\n")
            
    print(f"\nVerification complete. Results in {runs_dir}")
    print(f"Final Summary: {summary_path}")

if __name__ == "__main__":
    main()
