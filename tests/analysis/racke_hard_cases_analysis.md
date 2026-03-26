# Racke Hard Cases Queue/VC/Phase Analysis

This report reruns the hardest theory-7/6 permutations from `tests/data/results/2026/2026-03-25_193759__racke_corner_permutations__json_results__theory_guided_bucket_scan/racke_corner_perm_results.json` using their worst observed seed, then aggregates queue samples by phase, port, and VC.

## Case 1

- Permutation: `(4, 6, 7, 5, 8, 3, 2, 0, 1)`
- Cycle partition: `(7, 2)`
- Theory max-load edges: `24` edges at `7/6`
- Batch mean accepted rate: `0.745266`
- Worst seed replay: `seed=2`, `accepted=0.730944`, `latency=3163.24`
- Critical edges: `[(0, 1), (0, 3), (1, 2), (1, 4), (2, 5), (3, 4), (3, 6), (4, 5), (4, 7), (5, 8), (6, 7), (7, 8)]`
- Log: `tests/data/results/2026/2026-03-25_195127__racke_hard_cases__replay_logs__worst_seed_queue_analysis/hard_case_logs/hard_case_01.log`

Top phase buckets:

- phase0_scatter: mean window avg occupancy `56.32`, peak `72.02`
- phase1_middle: mean window avg occupancy `42.51`, peak `51.58`
- phase2_final: mean window avg occupancy `34.39`, peak `41.46`

Top node/port/phase buckets:

- Node `2` `inject` `phase2_final`: mean `7.65`, peak `7.86`
- Node `2` `inject` `phase0_scatter`: mean `7.64`, peak `7.89`
- Node `2` `inject` `phase1_middle`: mean `7.64`, peak `7.87`
- Node `1` `from_pos_x` `phase0_scatter`: mean `7.41`, peak `7.74`
- Node `1` `inject` `phase0_scatter`: mean `7.36`, peak `7.89`

Top VC hotspots:

- Node `2` `inject` VC `19` (phase2_final): mean `0.96`, peak `0.99`
- Node `2` `inject` VC `22` (phase2_final): mean `0.96`, peak `0.99`
- Node `2` `inject` VC `5` (phase0_scatter): mean `0.96`, peak `0.99`
- Node `2` `inject` VC `9` (phase1_middle): mean `0.96`, peak `0.99`
- Node `2` `inject` VC `23` (phase2_final): mean `0.96`, peak `0.98`

Notes:

- Dominant queue mass sits in phase0_scatter (mean window avg occupancy 56.32).
- Local injection queues remain active, with the hottest injection slice in phase1_middle at mean window avg occupancy 32.01.
- The hottest transit queue aligns with a theory-critical edge endpoint at node 1 from_pos_x (mean window avg occupancy 7.90).
- The single hottest node/port/phase bucket is node 2 inject in phase2_final (mean window avg occupancy 7.65).

## Case 2

- Permutation: `(2, 4, 6, 5, 7, 3, 8, 1, 0)`
- Cycle partition: `(4, 3, 2)`
- Theory max-load edges: `12` edges at `7/6`
- Batch mean accepted rate: `0.770374`
- Worst seed replay: `seed=2`, `accepted=0.730367`, `latency=4117.37`
- Critical edges: `[(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8)]`
- Log: `tests/data/results/2026/2026-03-25_195127__racke_hard_cases__replay_logs__worst_seed_queue_analysis/hard_case_logs/hard_case_02.log`

Top phase buckets:

- phase0_scatter: mean window avg occupancy `75.30`, peak `78.04`
- phase1_middle: mean window avg occupancy `71.61`, peak `73.06`
- phase2_final: mean window avg occupancy `48.33`, peak `49.62`

Top node/port/phase buckets:

- Node `2` `inject` `phase1_middle`: mean `7.69`, peak `7.77`
- Node `2` `inject` `phase2_final`: mean `7.64`, peak `7.66`
- Node `2` `inject` `phase0_scatter`: mean `7.63`, peak `7.67`
- Node `1` `from_pos_x` `phase0_scatter`: mean `7.38`, peak `7.44`
- Node `1` `inject` `phase1_middle`: mean `6.91`, peak `7.01`

Top VC hotspots:

- Node `2` `inject` VC `8` (phase1_middle): mean `0.97`, peak `0.99`
- Node `2` `inject` VC `18` (phase2_final): mean `0.97`, peak `1.00`
- Node `2` `inject` VC `6` (phase0_scatter): mean `0.97`, peak `0.98`
- Node `2` `inject` VC `9` (phase1_middle): mean `0.97`, peak `0.98`
- Node `2` `inject` VC `11` (phase1_middle): mean `0.97`, peak `0.98`

Notes:

- Dominant queue mass sits in phase0_scatter (mean window avg occupancy 75.30).
- Local injection queues remain active, with the hottest injection slice in phase0_scatter at mean window avg occupancy 44.14.
- The hottest transit queue aligns with a theory-critical edge endpoint at node 1 from_pos_x (mean window avg occupancy 7.46).
- The single hottest node/port/phase bucket is node 2 inject in phase1_middle (mean window avg occupancy 7.69).

## Case 3

- Permutation: `(4, 7, 6, 5, 8, 3, 2, 1, 0)`
- Cycle partition: `(3, 2, 2, 2)`
- Theory max-load edges: `24` edges at `7/6`
- Batch mean accepted rate: `0.773242`
- Worst seed replay: `seed=2`, `accepted=0.761200`, `latency=2731.36`
- Critical edges: `[(0, 1), (0, 3), (1, 2), (1, 4), (2, 5), (3, 4), (3, 6), (4, 5), (4, 7), (5, 8), (6, 7), (7, 8)]`
- Log: `tests/data/results/2026/2026-03-25_195127__racke_hard_cases__replay_logs__worst_seed_queue_analysis/hard_case_logs/hard_case_03.log`

Top phase buckets:

- phase0_scatter: mean window avg occupancy `63.47`, peak `68.49`
- phase1_middle: mean window avg occupancy `45.26`, peak `49.08`
- phase2_final: mean window avg occupancy `37.11`, peak `39.75`

Top node/port/phase buckets:

- Node `2` `inject` `phase1_middle`: mean `7.54`, peak `7.86`
- Node `2` `inject` `phase0_scatter`: mean `7.53`, peak `7.86`
- Node `2` `inject` `phase2_final`: mean `7.53`, peak `7.80`
- Node `1` `inject` `phase1_middle`: mean `7.09`, peak `7.87`
- Node `1` `inject` `phase0_scatter`: mean `7.05`, peak `7.83`

Top VC hotspots:

- Node `2` `inject` VC `11` (phase1_middle): mean `0.96`, peak `1.00`
- Node `2` `inject` VC `9` (phase1_middle): mean `0.96`, peak `0.99`
- Node `2` `inject` VC `1` (phase0_scatter): mean `0.95`, peak `1.00`
- Node `2` `inject` VC `23` (phase2_final): mean `0.95`, peak `0.99`
- Node `2` `inject` VC `5` (phase0_scatter): mean `0.95`, peak `0.99`

Notes:

- Dominant queue mass sits in phase0_scatter (mean window avg occupancy 63.47).
- Local injection queues remain active, with the hottest injection slice in phase2_final at mean window avg occupancy 33.95.
- The hottest transit queue aligns with a theory-critical edge endpoint at node 1 from_pos_x (mean window avg occupancy 7.04).
- The single hottest node/port/phase bucket is node 2 inject in phase1_middle (mean window avg occupancy 7.54).

## Case 4

- Permutation: `(4, 5, 7, 8, 6, 3, 2, 1, 0)`
- Cycle partition: `(9,)`
- Theory max-load edges: `24` edges at `7/6`
- Batch mean accepted rate: `0.778581`
- Worst seed replay: `seed=2`, `accepted=0.744778`, `latency=1343.28`
- Critical edges: `[(0, 1), (0, 3), (1, 2), (1, 4), (2, 5), (3, 4), (3, 6), (4, 5), (4, 7), (5, 8), (6, 7), (7, 8)]`
- Log: `tests/data/results/2026/2026-03-25_195127__racke_hard_cases__replay_logs__worst_seed_queue_analysis/hard_case_logs/hard_case_04.log`

Top phase buckets:

- phase0_scatter: mean window avg occupancy `84.99`, peak `93.19`
- phase1_middle: mean window avg occupancy `57.94`, peak `61.82`
- phase2_final: mean window avg occupancy `48.18`, peak `52.22`

Top node/port/phase buckets:

- Node `0` `inject` `phase1_middle`: mean `7.33`, peak `7.55`
- Node `0` `inject` `phase2_final`: mean `7.30`, peak `7.49`
- Node `0` `inject` `phase0_scatter`: mean `7.24`, peak `7.46`
- Node `5` `inject` `phase2_final`: mean `6.13`, peak `6.43`
- Node `5` `inject` `phase0_scatter`: mean `6.03`, peak `6.37`

Top VC hotspots:

- Node `0` `inject` VC `11` (phase1_middle): mean `0.93`, peak `0.97`
- Node `0` `inject` VC `22` (phase2_final): mean `0.93`, peak `0.95`
- Node `0` `inject` VC `14` (phase1_middle): mean `0.92`, peak `0.96`
- Node `0` `inject` VC `13` (phase1_middle): mean `0.92`, peak `0.95`
- Node `0` `inject` VC `19` (phase2_final): mean `0.92`, peak `0.95`

Notes:

- Dominant queue mass sits in phase0_scatter (mean window avg occupancy 84.99).
- Local injection queues remain active, with the hottest injection slice in phase2_final at mean window avg occupancy 42.55.
- The hottest transit queue aligns with a theory-critical edge endpoint at node 5 from_neg_y (mean window avg occupancy 6.87).
- The single hottest node/port/phase bucket is node 0 inject in phase1_middle (mean window avg occupancy 7.33).

## Case 5

- Permutation: `(1, 2, 7, 5, 8, 6, 4, 0, 3)`
- Cycle partition: `(5, 4)`
- Theory max-load edges: `14` edges at `7/6`
- Batch mean accepted rate: `0.779278`
- Worst seed replay: `seed=2`, `accepted=0.771500`, `latency=2936.15`
- Critical edges: `[(3, 4), (3, 6), (4, 5), (4, 7), (5, 8), (6, 7), (7, 8)]`
- Log: `tests/data/results/2026/2026-03-25_195127__racke_hard_cases__replay_logs__worst_seed_queue_analysis/hard_case_logs/hard_case_05.log`

Top phase buckets:

- phase0_scatter: mean window avg occupancy `58.50`, peak `66.36`
- phase1_middle: mean window avg occupancy `40.70`, peak `44.52`
- phase2_final: mean window avg occupancy `33.67`, peak `37.34`

Top node/port/phase buckets:

- Node `8` `inject` `phase2_final`: mean `7.52`, peak `7.89`
- Node `8` `inject` `phase0_scatter`: mean `7.49`, peak `7.82`
- Node `8` `inject` `phase1_middle`: mean `7.49`, peak `7.88`
- Node `7` `from_pos_x` `phase0_scatter`: mean `6.82`, peak `7.67`
- Node `3` `inject` `phase0_scatter`: mean `6.54`, peak `6.91`

Top VC hotspots:

- Node `8` `inject` VC `13` (phase1_middle): mean `0.95`, peak `1.00`
- Node `8` `inject` VC `20` (phase2_final): mean `0.95`, peak `0.99`
- Node `8` `inject` VC `19` (phase2_final): mean `0.95`, peak `1.00`
- Node `8` `inject` VC `4` (phase0_scatter): mean `0.95`, peak `0.98`
- Node `8` `inject` VC `18` (phase2_final): mean `0.94`, peak `0.99`

Notes:

- Dominant queue mass sits in phase0_scatter (mean window avg occupancy 58.50).
- Local injection queues remain active, with the hottest injection slice in phase2_final at mean window avg occupancy 31.23.
- The hottest transit queue aligns with a theory-critical edge endpoint at node 7 from_pos_x (mean window avg occupancy 7.51).
- The single hottest node/port/phase bucket is node 8 inject in phase2_final (mean window avg occupancy 7.52).
