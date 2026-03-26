---
name: booksim-saturation-scan
description: Use when running BookSim mesh or Racke saturation-throughput experiments, especially nonblocking speedup tests near the theoretical saturation point. Load doc/methodology_saturation_scan.md and enforce a small downward injection-rate scan so congestion collapse is not mistaken for a theory mismatch.
---

# BookSim Saturation Scan

Use this skill for saturation or accepted-rate studies in BookSim, especially `Racke` routing, permutation traffic, and `internal_speedup` / nonblocking speedup experiments.

## Required read

Before designing or interpreting the experiment, read:

- `doc/methodology_saturation_scan.md`

## Workflow

1. Compute the theoretical bottleneck load and target injection.
2. Run the target point.
3. Run several lower injection points near it.
   Recommended first pass: about `1%`, `2%`, and `3%` below the target, plus one slightly safer point if the cliff is sharp.
4. If the target point underperforms, compare with higher `VC` counts.
5. When presenting results, separate:
   - theoretical saturation point
   - best stable measured point near saturation
   - collapse point where extra injection reduces accepted throughput

## Reporting Guidance

When summarizing a saturation experiment, explicitly include:
- theoretical target injection
- scanned injection window
- best accepted rate in that window
- whether lowering injection improved throughput
- whether increasing `VC` improved throughput
