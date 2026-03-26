#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
from pathlib import Path

from artifact_layout import DATA_ROOT, INPUTS_ROOT, RESULTS_ROOT, write_readme


REPO_ROOT = DATA_ROOT.parents[1]


def repo_relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def move_file(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def move_tree_contents(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.exists():
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    for child in sorted(src_dir.iterdir()):
        shutil.move(str(child), str(dst_dir / child.name))
    src_dir.rmdir()


def update_runs_json_configs(runs_dir: Path) -> None:
    for json_path in runs_dir.glob("*.json"):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        config_value = payload.get("config")
        if isinstance(config_value, str):
            payload["config"] = Path(config_value).name
            json_path.write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")


def update_hard_case_json_paths(json_path: Path, logs_dir: Path) -> None:
    if not json_path.exists():
        return
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    for case in payload.get("cases", []):
        if "config_path" in case:
            case["config_path"] = repo_relative(logs_dir / Path(case["config_path"]).name)
        if "log_path" in case:
            case["log_path"] = repo_relative(logs_dir / Path(case["log_path"]).name)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def update_json_path_fields(json_path: Path, replacements: dict[str, str]) -> None:
    if not json_path.exists():
        return
    text = json_path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    json_path.write_text(text, encoding="utf-8")


def main() -> None:
    inputs_configs = INPUTS_ROOT / "configs"
    inputs_maps = INPUTS_ROOT / "maps"
    results_2026 = RESULTS_ROOT / "2026"

    write_readme(
        DATA_ROOT,
        title="tests/data",
        content="test artifacts root",
        artifact_type="dataset index",
        purpose="separate stable inputs from time-organized experimental results",
        notes=[
            "Stable inputs live under inputs/.",
            "Generated and archived results live under results/<year>/.",
        ],
    )
    write_readme(
        INPUTS_ROOT,
        title="inputs",
        content="stable test inputs",
        artifact_type="input assets",
        purpose="preserve reusable configs and maps outside time-stamped result archives",
    )
    write_readme(
        inputs_configs,
        title="configs",
        content="stable experiment configs",
        artifact_type="configuration files",
        purpose="reusable BookSim config inputs for verification and replay scripts",
    )
    write_readme(
        inputs_maps,
        title="maps",
        content="stable mapping files",
        artifact_type="mapping assets",
        purpose="reusable topology and mapping inputs",
    )
    write_readme(
        RESULTS_ROOT,
        title="results",
        content="archived experiment outputs",
        artifact_type="time-organized result folders",
        purpose="group generated artifacts by execution time, content, type, and purpose",
    )
    write_readme(
        results_2026,
        title="2026",
        content="2026 experiment archives",
        artifact_type="year bucket",
        purpose="group 2026 result folders by execution timestamp",
    )

    move_file(DATA_ROOT / "dsl_3x3.config", inputs_configs / "dsl_3x3.config")
    move_file(DATA_ROOT / "racke_tree_3x3_limit.config", inputs_configs / "racke_tree_3x3_limit.config")
    move_file(DATA_ROOT / "test_dynamic.config", inputs_configs / "test_dynamic.config")
    move_file(DATA_ROOT / "map_2x2.txt", inputs_maps / "map_2x2.txt")

    folder_20260320_mesh = results_2026 / "2026-03-20_161823__mesh_baseline__json_results__detail_export"
    write_readme(
        folder_20260320_mesh,
        title=folder_20260320_mesh.name,
        content="mesh baseline",
        artifact_type="json results",
        purpose="detail export from early detailed BookSim result runs",
        notes=["Primary artifact: test_results_detailed.json"],
    )
    move_file(DATA_ROOT / "test_results_detailed.json", folder_20260320_mesh / "test_results_detailed.json")

    folder_20260320_viz = results_2026 / "2026-03-20_172807__hypercube_embedding__visualizations__gray_mesh4x4"
    write_readme(
        folder_20260320_viz,
        title=folder_20260320_viz.name,
        content="hypercube embedding",
        artifact_type="visualizations",
        purpose="store generated 4x4 mesh embedding visualization assets",
        notes=["Contains dot, svg, and png renderings."],
    )
    move_tree_contents(DATA_ROOT / "visualizations", folder_20260320_viz)

    folder_20260324_racke = results_2026 / "2026-03-24_142949__racke_baseline__json_results__detail_export"
    write_readme(
        folder_20260324_racke,
        title=folder_20260324_racke.name,
        content="racke baseline",
        artifact_type="json results",
        purpose="detail export from baseline Racke result runs",
        notes=["Primary artifact: test_results_detailed_racke.json"],
    )
    move_file(DATA_ROOT / "test_results_detailed_racke.json", folder_20260324_racke / "test_results_detailed_racke.json")

    folder_20260324_verify_summary = results_2026 / "2026-03-24_190020__racke_dsl_limit_verification__summary_log__legacy_seed_table"
    write_readme(
        folder_20260324_verify_summary,
        title=folder_20260324_verify_summary.name,
        content="racke and dsl limit verification",
        artifact_type="summary log",
        purpose="preserve a legacy root-level throughput summary table under the time-organized archive layout",
        notes=[
            "Primary artifact: verification_summary.log",
            "Imported from the historical tests/data/run.log artifact when present.",
        ],
    )
    move_file(DATA_ROOT / "run.log", folder_20260324_verify_summary / "verification_summary.log")

    folder_20260325_verify = results_2026 / "2026-03-25_185003__racke_dsl_limit_verification__seed_runs__latency_limit_scan"
    verify_runs = folder_20260325_verify / "runs"
    write_readme(
        folder_20260325_verify,
        title=folder_20260325_verify.name,
        content="racke dsl limit verification",
        artifact_type="seed runs",
        purpose="store per-seed latency-limit verification runs for Racke and DSL",
        notes=["Raw per-run files live under runs/."],
    )
    write_readme(
        verify_runs,
        title=verify_runs.name,
        content="verification seed runs",
        artifact_type="raw run artifacts",
        purpose="preserve generated config, log, and json triplets for each verification run",
    )
    move_tree_contents(DATA_ROOT / "runs", verify_runs)
    update_runs_json_configs(verify_runs)

    folder_20260325_corner = results_2026 / "2026-03-25_193759__racke_corner_permutations__json_results__theory_guided_bucket_scan"
    write_readme(
        folder_20260325_corner,
        title=folder_20260325_corner.name,
        content="racke corner permutations",
        artifact_type="json results",
        purpose="store theory-guided bucketed permutation scan results for 3x3 Racke",
        notes=["Primary artifact: racke_corner_perm_results.json"],
    )
    move_file(DATA_ROOT / "racke_corner_perm_results.json", folder_20260325_corner / "racke_corner_perm_results.json")

    folder_20260325_hard = results_2026 / "2026-03-25_195127__racke_hard_cases__replay_logs__worst_seed_queue_analysis"
    hard_logs = folder_20260325_hard / "hard_case_logs"
    write_readme(
        folder_20260325_hard,
        title=folder_20260325_hard.name,
        content="racke hard cases",
        artifact_type="replay logs and analysis",
        purpose="store worst-seed hard-case replay logs and aggregated queue analysis",
        notes=[
            "Primary artifact: racke_hard_cases_analysis.json",
            "Per-case raw logs live under hard_case_logs/.",
        ],
    )
    write_readme(
        hard_logs,
        title=hard_logs.name,
        content="hard-case replay logs",
        artifact_type="raw config and log files",
        purpose="preserve hard_case_XX replay configs and BookSim console output",
        notes=["Raw log headers are preserved verbatim and may still mention the original capture paths."],
    )
    move_tree_contents(DATA_ROOT / "racke_hard_case_logs", hard_logs)
    move_file(DATA_ROOT / "racke_hard_cases_analysis.json", folder_20260325_hard / "racke_hard_cases_analysis.json")
    update_hard_case_json_paths(folder_20260325_hard / "racke_hard_cases_analysis.json", hard_logs)

    folder_20260325_sweeps = results_2026 / "2026-03-25_201940__racke_hard_cases__sweep_results__inj_and_vc_sweep"
    write_readme(
        folder_20260325_sweeps,
        title=folder_20260325_sweeps.name,
        content="racke hard cases",
        artifact_type="sweep results",
        purpose="store injection-rate and VC-count sweep summaries for hard cases",
        notes=["Primary artifact: racke_hard_sweeps.json"],
    )
    move_file(DATA_ROOT / "racke_hard_sweeps.json", folder_20260325_sweeps / "racke_hard_sweeps.json")

    folder_20260326_compare = results_2026 / "2026-03-26_131457__racke_hard_cases__comparison_results__vc_vs_noq_single_output"
    write_readme(
        folder_20260326_compare,
        title=folder_20260326_compare.name,
        content="racke hard cases",
        artifact_type="comparison results",
        purpose="compare VC against single-output NOQ on matched hard cases",
        notes=["Primary artifact: racke_voq_vs_vc.json"],
    )
    move_file(DATA_ROOT / "racke_voq_vs_vc.json", folder_20260326_compare / "racke_voq_vs_vc.json")

    folder_20260326_vc_focus = results_2026 / "2026-03-26_133113__racke_hard_cases__sweep_results__vc_focus_saturation_scan"
    write_readme(
        folder_20260326_vc_focus,
        title=folder_20260326_vc_focus.name,
        content="racke hard cases",
        artifact_type="sweep results",
        purpose="store VC-focused saturation scan results and one-line pass summaries",
        notes=[
            "Primary artifact: racke_hard_sweeps_vc_focus.json",
            "Pass-summary log: racke_hard_sweeps_vc_focus_pass.log",
        ],
    )
    move_file(DATA_ROOT / "racke_hard_sweeps_vc_focus.json", folder_20260326_vc_focus / "racke_hard_sweeps_vc_focus.json")
    move_file(DATA_ROOT / "racke_hard_sweeps_vc_focus_pass.log", folder_20260326_vc_focus / "racke_hard_sweeps_vc_focus_pass.log")

    racke_corner_json = folder_20260325_corner / "racke_corner_perm_results.json"
    racke_hard_analysis_json = folder_20260325_hard / "racke_hard_cases_analysis.json"
    racke_hard_sweeps_json = folder_20260325_sweeps / "racke_hard_sweeps.json"
    racke_compare_json = folder_20260326_compare / "racke_voq_vs_vc.json"
    racke_vc_focus_json = folder_20260326_vc_focus / "racke_hard_sweeps_vc_focus.json"
    racke_vc_focus_log = folder_20260326_vc_focus / "racke_hard_sweeps_vc_focus_pass.log"
    replacements = {
        "tests/data/racke_hard_case_logs": repo_relative(hard_logs),
        str(DATA_ROOT / "racke_hard_case_logs"): repo_relative(hard_logs),
        "tests/data/racke_corner_perm_results.json": repo_relative(racke_corner_json),
        str(DATA_ROOT / "racke_corner_perm_results.json"): repo_relative(racke_corner_json),
        str(racke_corner_json): repo_relative(racke_corner_json),
        "tests/data/racke_hard_cases_analysis.json": repo_relative(racke_hard_analysis_json),
        str(DATA_ROOT / "racke_hard_cases_analysis.json"): repo_relative(racke_hard_analysis_json),
        str(racke_hard_analysis_json): repo_relative(racke_hard_analysis_json),
        "tests/data/racke_hard_sweeps.json": repo_relative(racke_hard_sweeps_json),
        str(DATA_ROOT / "racke_hard_sweeps.json"): repo_relative(racke_hard_sweeps_json),
        str(racke_hard_sweeps_json): repo_relative(racke_hard_sweeps_json),
        "tests/data/racke_voq_vs_vc.json": repo_relative(racke_compare_json),
        str(DATA_ROOT / "racke_voq_vs_vc.json"): repo_relative(racke_compare_json),
        str(racke_compare_json): repo_relative(racke_compare_json),
        "tests/data/racke_hard_sweeps_vc_focus.json": repo_relative(racke_vc_focus_json),
        str(DATA_ROOT / "racke_hard_sweeps_vc_focus.json"): repo_relative(racke_vc_focus_json),
        str(racke_vc_focus_json): repo_relative(racke_vc_focus_json),
        "tests/data/racke_hard_sweeps_vc_focus_pass.log": repo_relative(racke_vc_focus_log),
        str(DATA_ROOT / "racke_hard_sweeps_vc_focus_pass.log"): repo_relative(racke_vc_focus_log),
        str(racke_vc_focus_log): repo_relative(racke_vc_focus_log),
    }
    update_json_path_fields(racke_hard_sweeps_json, replacements)
    update_json_path_fields(racke_compare_json, replacements)
    update_json_path_fields(racke_vc_focus_json, replacements)


if __name__ == "__main__":
    main()
