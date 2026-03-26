# RackeTree / DSL Reproduction Guide

This document is the project-level runbook for teammates who need to build BookSim and reproduce the current `3x3` Mesh `RackeTree` and `DSL` simulations.

## Scope

- Topology: `3x3` mesh (`k = 3`, `n = 2`)
- Routing functions:
  - `racke_tree`
  - `dsl`
- Stable base configs:
  - `tests/data/inputs/configs/racke_tree_3x3_limit.config`
  - `tests/data/inputs/configs/dsl_3x3.config`
- Verification driver:
  - `tests/scripts/verify_saturation_limit.py`

## Build

From the repository root:

```bash
make -C src
```

The expected simulator binary is:

```text
src/booksim
```

## Direct Smoke Runs

These commands confirm that both routing functions are registered and runnable before doing any batch verification:

```bash
src/booksim tests/data/inputs/configs/racke_tree_3x3_limit.config
src/booksim tests/data/inputs/configs/dsl_3x3.config
```

Expected signals:

- the config is accepted without a routing-function error
- the run exits cleanly without `Simulation unstable`
- the output includes accepted-rate and latency summaries

## Batch Verification Script

From the repository root, run:

```bash
python3 tests/scripts/verify_saturation_limit.py \
  --algos racke dsl \
  --traffics randperm dynamic_perm \
  --seeds 118 119 \
  --output-dir /tmp/racke_dsl_smoke
```

Notes:

- The script now resolves `src/booksim` relative to the repository root by default.
- `--output-dir` is recommended for smoke runs so the repo does not accumulate ad hoc result folders.
- If omitted, results go under `tests/data/results/<year>/...`.
- If you run only `--algos racke dsl`, the script uses its full default sweep: 30 seeds and both `randperm` / `dynamic_perm`.

## Important Overrides Applied By The Script

The script rewrites these keys on top of the base configs for each generated run:

- `injection_rate`
- `perm_seed`
- `traffic`
- `num_vcs`
- `vc_buf_size`
- `internal_speedup`
- `alloc_iters`

Current defaults used by the script:

- `num_vcs = 48`
- `vc_buf_size = 16`
- `internal_speedup = 2.0`
- `alloc_iters = 16`
- `racke_rate = 0.8571`
- `dsl_rate = 0.75`

## VC Constraints

The route implementation in `src/routefunc.cpp` partitions VCs by phase:

- `DSL` uses `2` phases, so each traffic class should have at least `2` VCs.
- `RackeTree` uses `3` phases, so each traffic class should have at least `3` VCs.

For the current verification workflow, use the script defaults above unless you are intentionally sweeping VC counts.

## Methodology Notes

For saturation-limit interpretation, do not rely on a single point near theory. Follow:

- `doc/methodology_saturation_scan.md`

Relevant theory / analysis references:

- `tests/analysis/deadlock_analysis.md`
- `tests/analysis/rackeTree_col_row_embedding_analysis.py`
- `tests/analysis/racke_worst_case.py`
- `tests/analysis/dsl_exhaustive_analysis.py`

## Troubleshooting

- If `src/booksim` is missing, run `make -C src`.
- If a teammate runs the script from the repo root, no extra path adjustment is needed.
- If the theory point underperforms, scan slightly below the target injection before claiming a theory mismatch.
