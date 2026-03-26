# configs

- Content: stable experiment configs
- Type: configuration files
- Purpose: reusable BookSim config inputs for verification and replay scripts

## Files

- `racke_tree_3x3_limit.config`
  Base `3x3` Mesh config for `routing_function = racke_tree`.
- `dsl_3x3.config`
  Base `3x3` Mesh config for `routing_function = dsl`.

## Usage

- Direct run:
  - `src/booksim tests/data/inputs/configs/racke_tree_3x3_limit.config`
  - `src/booksim tests/data/inputs/configs/dsl_3x3.config`
- Batch verification:
  - `python3 tests/scripts/verify_saturation_limit.py --algos racke dsl --traffics randperm --seeds 118 --output-dir /tmp/racke_dsl_smoke`

## Notes

- `tests/scripts/verify_saturation_limit.py` rewrites `injection_rate`, `perm_seed`, `traffic`, `num_vcs`, `vc_buf_size`, `internal_speedup`, and `alloc_iters` per generated run.
- If you omit `--seeds` and `--traffics`, the script runs the full default verification sweep across 30 seeds and both `randperm` / `dynamic_perm`.
- See `doc/methodology_racke_dsl_repro.md` for the full runbook.
