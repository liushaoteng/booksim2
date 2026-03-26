BookSim Interconnection Network Simulator
=========================================

BookSim is a cycle-accurate interconnection network simulator.
Originally developed for and introduced with the [Principles and Practices of Interconnection Networks](http://cva.stanford.edu/books/ppin/) book, its functionality has since been continuously extended.
The current major release, BookSim 2.0, supports a wide range of topologies such as mesh, torus and flattened butterfly networks, provides diverse routing algorithms and includes numerous options for customizing the network's router microarchitecture.

---

Project-specific reproduction notes for the current `RackeTree` / `DSL` `3x3` Mesh work live in:

- `doc/methodology_racke_dsl_repro.md`

Build the simulator from the repository root with:

```bash
make -C src
```

Quick smoke runs:

```bash
src/booksim tests/data/inputs/configs/racke_tree_3x3_limit.config
src/booksim tests/data/inputs/configs/dsl_3x3.config
```

Batch verification:

```bash
python3 tests/scripts/verify_saturation_limit.py \
  --algos racke dsl \
  --traffics randperm \
  --seeds 118 \
  --output-dir /tmp/racke_dsl_smoke
```

---

If you use BookSim in your research, we would appreciate the following citation in any publications to which it has contributed:

Nan Jiang, Daniel U. Becker, George Michelogiannakis, James Balfour, Brian Towles, John Kim and William J. Dally. A Detailed and Flexible Cycle-Accurate Network-on-Chip Simulator. In *Proceedings of the 2013 IEEE International Symposium on Performance Analysis of Systems and Software*, 2013.
