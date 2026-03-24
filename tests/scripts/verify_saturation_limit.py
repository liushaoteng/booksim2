import subprocess
import re
import os
import json

# Configuration
RACKE_CONFIG = "../data/racke_tree_3x3_limit.config"
DSL_CONFIG = "../data/dsl_3x3.config"
SEEDS = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
RACKE_LIMIT = 0.8571  # 6/7
DSL_LIMIT = 0.75      # 1/1.33

def run_point(config, rate, seed, routing=None, speedup=2.0, buf_size=4, allocator="islip", traffic="dynamic_perm"):
    cmd = [
        "../../src/booksim",
        config,
        f"traffic={traffic}({seed})",
        f"injection_rate={rate}",
        "num_vcs=24",
        f"vc_buf_size={buf_size}",
        f"internal_speedup={speedup}",
        f"vc_allocator={allocator}",
        f"sw_allocator={allocator}",
        "warmup_periods=20",
        "sample_period=2000",
        "max_samples=40",
        "queue_sample_period_cycles=100"
    ]
    if routing:
        cmd.append(f"routing_function={routing}")
        
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        output = result.stdout
        
        # Parse Acc Rate
        acc_match = re.search(r'Accepted packet rate average = ([\d\.]+)', output)
        acc_rate = float(acc_match.group(1)) if acc_match else 0.0
        
        # Parse Latency
        lat_match = re.search(r'Packet latency average = ([\d\.]+)', output)
        avg_lat = float(lat_match.group(1)) if lat_match else 0.0
        
        # Parse Queue Max
        queue_blocks = re.split(r'====== Queue Sample Statistics', output)
        last_q = queue_blocks[-1]
        max_vals = re.findall(r'max: (\d+)', last_q)
        q_max = max(int(v) for v in max_vals) if max_vals else 0
        
        return acc_rate, avg_lat, q_max
    except:
        return 0.0, 0.0, 0

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    SPEEDUP = 2.0
    BUF_SIZE = 4
    ALLOCATOR = "islip"
    TRAFFIC = "dynamic_perm"
    
    print(f"Testing with Speedup={SPEEDUP}, BufSize={BUF_SIZE}, Allocator={ALLOCATOR}, Traffic={TRAFFIC}")
    print(f"{'Algo':<10} | {'Seed':<5} | {'Limit':<8} | {'Accepted':<8} | {'Latency':<8} | {'MaxQ':<5}")
    print("-" * 60)
    
    results = []
    
    # 1. Test RackeTree
    for s in SEEDS:
        acc, lat, qm = run_point(RACKE_CONFIG, RACKE_LIMIT, s, "racke_tree", speedup=SPEEDUP, buf_size=BUF_SIZE, allocator=ALLOCATOR, traffic=TRAFFIC)
        print(f"{'Racke':<10} | {s:<5} | {RACKE_LIMIT:<8.4f} | {acc:<8.4f} | {lat:<8.2f} | {qm:<5}")
        results.append({"algo": "RackeTree", "seed": s, "acc": acc, "lat": lat, "max_q": qm})
        
    # 2. Test DSL
    for s in SEEDS:
        acc, lat, qm = run_point(DSL_CONFIG, DSL_LIMIT, s, "dsl", speedup=SPEEDUP, buf_size=BUF_SIZE, allocator=ALLOCATOR, traffic=TRAFFIC)
        print(f"{'DSL':<10} | {s:<5} | {DSL_LIMIT:<8.4f} | {acc:<8.4f} | {lat:<8.2f} | {qm:<5}")
        results.append({"algo": "DSL", "seed": s, "acc": acc, "lat": lat, "max_q": qm})

    # Update summary log
    with open("../data/run.log", "w") as f:
        f.write(f"BookSim Saturation Limit Robustness Log (Speedup={SPEEDUP}, Buf={BUF_SIZE}, Alloc={ALLOCATOR}, Traffic={TRAFFIC})\n")
        f.write("=" * 60 + "\n")
        f.write(f"{'Algo':<10} | {'Seed':<5} | {'Limit':<8} | {'Accepted':<8} | {'MaxQ':<5}\n")
        f.write("-" * 60 + "\n")
        for r in results:
            f.write(f"{r['algo']:<10} | {r['seed']:<5} | {0.8571 if r['algo']=='RackeTree' else 0.75:<8.4f} | {r['acc']:<8.4f} | {r['max_q']:<5}\n")
    
    print("\nSummary written to tests/data/run.log")

if __name__ == "__main__":
    main()
