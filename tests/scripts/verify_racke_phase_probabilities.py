#!/usr/bin/env python3

import argparse
import collections
import itertools
from fractions import Fraction


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that the current racke_tree_mesh implementation realizes the "
            "expected 1/2 rule-family split and uniform intermediate balancing."
        )
    )
    parser.add_argument("--k", type=int, default=3)
    return parser.parse_args()


def get_path_xy(u: int, v: int, k: int) -> list[tuple[int, int]]:
    ux, uy = u % k, u // k
    vx, vy = v % k, v // k
    path = []
    cur_x, cur_y = ux, uy
    while cur_x != vx:
        step = 1 if vx > cur_x else -1
        next_x = cur_x + step
        path.append((cur_y * k + cur_x, cur_y * k + next_x))
        cur_x = next_x
    while cur_y != vy:
        step = 1 if vy > cur_y else -1
        next_y = cur_y + step
        path.append((cur_y * k + cur_x, next_y * k + cur_x))
        cur_y = next_y
    return path


def add_path(edges: collections.defaultdict[tuple[int, int], Fraction], u: int, v: int, weight: Fraction, k: int) -> None:
    for edge in get_path_xy(u, v, k):
        edges[edge] += weight


def expected_pair_contribution(u: int, v: int, k: int) -> dict[tuple[int, int], Fraction]:
    ux, uy = u % k, u // k
    vx, vy = v % k, v // k
    edges: collections.defaultdict[tuple[int, int], Fraction] = collections.defaultdict(Fraction)

    if u == v:
        return {}

    if uy == vy:
        add_path(edges, u, v, Fraction(1, 2), k)
    else:
        for mid_x in range(k):
            row_node = uy * k + mid_x
            col_node = vy * k + mid_x
            weight = Fraction(1, 2 * k)
            add_path(edges, u, row_node, weight, k)
            add_path(edges, row_node, col_node, weight, k)
            add_path(edges, col_node, v, weight, k)

    if ux == vx:
        add_path(edges, u, v, Fraction(1, 2), k)
    else:
        for mid_y in range(k):
            col_node = mid_y * k + ux
            row_node = mid_y * k + vx
            weight = Fraction(1, 2 * k)
            add_path(edges, u, col_node, weight, k)
            add_path(edges, col_node, row_node, weight, k)
            add_path(edges, row_node, v, weight, k)

    return dict(edges)


def simulated_pair_contribution(
    src: int, dest: int, k: int
) -> tuple[dict[tuple[int, int], Fraction], dict[str, collections.Counter]]:
    period = 2 * k
    start_rr = (src + dest) % period
    edges: collections.defaultdict[tuple[int, int], Fraction] = collections.defaultdict(Fraction)
    stats = {
        "rule_family": collections.Counter(),
        "rule2_mid_x": collections.Counter(),
        "rule3_mid_y": collections.Counter(),
        "terminal_phase": collections.Counter(),
    }

    src_row = src // k
    src_col = src % k
    dest_row = dest // k
    dest_col = dest % k

    for offset in range(period):
        rr_val = start_rr + offset
        weight = Fraction(1, period)
        rule = 2 if (rr_val % 2 == 0) else 3

        if rule == 2:
            stats["rule_family"]["rule2"] += 1
            if src_row == dest_row:
                stats["terminal_phase"]["phase2_direct"] += 1
                add_path(edges, src, dest, weight, k)
            else:
                mid_x = (rr_val // 2) % k
                stats["rule2_mid_x"][mid_x] += 1
                row_node = src_row * k + mid_x
                col_node = dest_row * k + mid_x
                add_path(edges, src, row_node, weight, k)
                add_path(edges, row_node, col_node, weight, k)
                add_path(edges, col_node, dest, weight, k)
        else:
            stats["rule_family"]["rule3"] += 1
            if src_col == dest_col:
                stats["terminal_phase"]["phase12_direct"] += 1
                add_path(edges, src, dest, weight, k)
            else:
                mid_y = (rr_val // 2) % k
                stats["rule3_mid_y"][mid_y] += 1
                col_node = mid_y * k + src_col
                row_node = mid_y * k + dest_col
                add_path(edges, src, col_node, weight, k)
                add_path(edges, col_node, row_node, weight, k)
                add_path(edges, row_node, dest, weight, k)

    return dict(edges), stats


def verify_pair(src: int, dest: int, k: int) -> None:
    expected = expected_pair_contribution(src, dest, k)
    observed, stats = simulated_pair_contribution(src, dest, k)
    period = 2 * k

    if stats["rule_family"]["rule2"] != k or stats["rule_family"]["rule3"] != k:
        raise AssertionError(
            f"({src}->{dest}) rule-family split mismatch: {stats['rule_family']}"
        )

    src_row = src // k
    src_col = src % k
    dest_row = dest // k
    dest_col = dest % k

    if src_row != dest_row:
        expected_mid = collections.Counter({mid_x: 1 for mid_x in range(k)})
        if stats["rule2_mid_x"] != expected_mid:
            raise AssertionError(
                f"({src}->{dest}) rule2 mid-x imbalance: {stats['rule2_mid_x']}"
            )
    else:
        if stats["terminal_phase"]["phase2_direct"] != k:
            raise AssertionError(
                f"({src}->{dest}) rule2 direct mass mismatch: {stats['terminal_phase']}"
            )

    if src_col != dest_col:
        expected_mid = collections.Counter({mid_y: 1 for mid_y in range(k)})
        if stats["rule3_mid_y"] != expected_mid:
            raise AssertionError(
                f"({src}->{dest}) rule3 mid-y imbalance: {stats['rule3_mid_y']}"
            )
    else:
        if stats["terminal_phase"]["phase12_direct"] != k:
            raise AssertionError(
                f"({src}->{dest}) rule3 direct mass mismatch: {stats['terminal_phase']}"
            )

    if observed != expected:
        all_edges = sorted(set(expected) | set(observed))
        deltas = [
            (edge, expected.get(edge, Fraction(0, 1)), observed.get(edge, Fraction(0, 1)))
            for edge in all_edges
            if expected.get(edge, Fraction(0, 1)) != observed.get(edge, Fraction(0, 1))
        ]
        raise AssertionError(f"({src}->{dest}) edge contribution mismatch: {deltas[:8]}")


def main() -> None:
    args = parse_args()
    nodes = list(range(args.k * args.k))

    for src, dest in itertools.product(nodes, nodes):
        if src == dest:
            continue
        verify_pair(src, dest, args.k)

    print(
        f"PASS: verified Racke phase balancing for all {len(nodes) * (len(nodes) - 1)} "
        f"ordered pairs on a {args.k}x{args.k} mesh."
    )
    print(
        "Each flow realizes an exact 1/2 Rule-2 + 1/2 Rule-3 split, and every "
        "eligible intermediate row/column choice appears exactly once per 2K-packet period."
    )


if __name__ == "__main__":
    main()
