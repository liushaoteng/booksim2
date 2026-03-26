# Deadlock Analysis: RackeTree and DSL on 3x3 Mesh

This document provides a formal deadlock analysis for the **RackeTree** and **Distributed Spine-Leaf (DSL)** routing algorithms as implemented in BookSim, referencing the principles of deadlock avoidance from Dally's "Principles and Practices of Interconnection Networks".

## 1. Background: Dally's Deadlock Avoidance Theory

According to Dally (Chapter 14/15), a routing algorithm is deadlock-free if its **Channel Dependency Graph (CDG)** is acyclic. For non-oblivious or multi-phase routing algorithms, deadlocks can be avoided by:
1.  **Dimension Order Routing (DOR)**: Restricting the order of dimension traversal (e.g., X then Y) to prevent cycles within a single network layer.
2.  **Resource Ordering (VC Partitioning)**: Dividing Virtual Channels (VCs) into disjoint sets and restricting transitions between these sets to follow a strict partial order.

---

## 2. Distributed Spine-Leaf (DSL) Analysis

### Algorithm Structure
DSL (Packet Spraying VLB) is a 2-phase routing algorithm:
- **Phase 0**: Source node $S$ routes to a chosen intermediate node $W$ using XY routing.
- **Phase 1**: Intermediate node $W$ routes to destination $D$ using XY routing.

### Deadlock Avoidance Mechanism
DSL uses **Phase-based VC Partitioning** (Resource Ordering):
- The VC range $[VC_{begin}, VC_{end}]$ is split into two equal halves.
- **Set 0** (Lower half) is used exclusively for Phase 0.
- **Set 1** (Upper half) is used exclusively for Phase 1.

### Proof of Deadlock Freedom
1.  **Intra-Phase**: Within each phase, the algorithm uses XY (Dimension Order) routing. In a mesh topology, XY routing is known to be acyclic.
2.  **Inter-Phase**: Packets only transition from Set 0 to Set 1 (when reaching $W$) or stay within a set. There is no transition from Set 1 back to Set 0.
3.  **Result**: Since neither phase has internal cycles and there are no back-dependencies between VC sets, the overall CDG is acyclic. **DSL is deadlock-free.**

---

## 3. RackeTree Analysis

### Algorithm Structure
RackeTree uses a hierarchical scattering approach. For a 3x3 Mesh, it effectively uses a 3-phase routing process depending on the scattering rule (Rule 2 or Rule 3):
- **Rule 2 (Row-Scatter)**:
    - Phase 0: X-Scatter (Current Row)
    - Phase 1: Y-Move (To Target Row)
    - Phase 2: X-Move (To Final Destination)
- **Rule 3 (Col-Scatter)**:
    - Phase 10: Y-Scatter (Current Column)
    - Phase 11: X-Move (To Target Column)
    - Phase 12: Y-Move (To Final Destination)

### Deadlock Avoidance Mechanism
RackeTree uses **3-Phase VC Partitioning**:
- The VC range $[VC_{begin}, VC_{end}]$ is divided into 3 disjoint sets.
- **VC Set 0**: Used for Phases 0 and 10.
- **VC Set 1**: Used for Phases 1 and 11.
- **VC Set 2**: Used for Phases 2 and 12.

### Proof of Deadlock Freedom
1.  **Intra-Phase Consistency**: Each phase performs movement only along a *single dimension* at a time (X or Y). A single-dimension movement in a mesh is inherently acyclic (no "turns").
2.  **Strict Phase Ordering**:
    - For Rule 2: Transitions follow $Set 0 \to Set 1 \to Set 2$.
    - For Rule 3: Transitions follow $Set 0 \to Set 1 \to Set 2$.
3.  **Acyclic Dependency**: Because transitions between VC classes are strictly monotonic (increasing), no cycle can be formed that spans across different phases.
4.  **Result**: The Channel Dependency Graph for RackeTree is acyclic. **RackeTree is deadlock-free.**

---

## 4. Conclusion
Both algorithms leverage **Resource Ordering** via Virtual Channels to complement their multi-phase nature.
- **DSL** requires at least **2 VCs** per traffic class (one per phase).
- **RackeTree** requires at least **3 VCs** per traffic class (one per phase).

The implementation in `src/routefunc.cpp` correctly enforces these constraints by dynamically calculating `vcs_per_phase` and steering flits into the appropriate VC range based on their current `ph` (phase) metadata.
