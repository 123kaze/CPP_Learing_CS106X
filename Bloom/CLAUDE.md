# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What lives here

`Bloom/` holds two generations of learned-Bloom-filter research code:

- **Top-level scripts** (`Bloom.py`, `evaluate_*.py`, `compare_*.py`, `tune_student_*.py`, `teacher_query_aware_gama.py`, …): an older "LightTree-PLBF student vs. teacher Gama-LBF" study, written up in `做了什么..md` / `实验结果.md`. They expect the teacher repo checked out at `LBF-Gama/` (the submodule is empty apart from `LBF-Gama/dataset/raw/cod/`) and use scikit-learn, which is not in the project env. Treat them as legacy.
- **`learned_adaptive_hybrid/`**: the active project, which extends Gama's memory allocation with a negative-key cache ("Gama＋缓存"; Gama is the cache share r = 0 special case). All recent work is here. Its `README.md` has the full directory map, every run command, and the data/feature conventions. `docs/决策记录.md` is the dated decision log, and `docs/问题定义.md` holds the problem definition and status table. Both are in Chinese, as are all result write-ups (`results/expN_*/结论.md`).

## Environment and running

- Python is a self-contained conda-forge env at `Bloom/.condaenv` (pip's lightgbm lacks libomp on this Mac). Always run from `learned_adaptive_hybrid/` as `../.condaenv/bin/python -u src/<script>.py`. Scripts import each other as plain modules (`import common as C`, `from exp9_fp_stream_controller import …`), so they must be launched from `src/` on the path like this.
- There is no test suite or linter. Correctness checks are built into the experiments: zero-false-negative asserts in `common.Structure` and the external drivers, plus regression checks where a refactor must reproduce earlier `rows.json` exactly.
- Fastest end-to-end smoke test is the real-trace dataset (~20 s): `../.condaenv/bin/python -u src/exp13_deployable.py --dataset caida_flow`. Most experiment scripts accept `--seeds`, `--dataset`, `--budgets` (KiB, comma-separated) and `--suffix`, and most have `--report`, which merges `results/<exp>/rows_*.json` into `report.md`/`summary.json`.
- `src/plot_figures.py` regenerates every figure in `figures/` from the result JSONs. It skips a figure when that figure's inputs are missing.
- External C/C++ drivers (`external/aqf_port/aqf_driver`, `external/stacked_port/stacked_driver`) have their build commands in the project README. Both wrap unmodified upstream code from the How-to-Train-Your-Filter repo (`external/How-to-Train-Your-Filter`, pinned at c970c34) with ARM/clang compatibility patches.

## Architecture (`src/common.py` is the core)

- **Datasets.** The `DATASETS` registry plus `load_dataset(name)` load and cache to `cache/<name>/data.npz`. `split_and_score` assigns members and negatives to splits by hashing the key (training / validation / test-pool negatives are disjoint). It also trains the 48-tree LightGBM and caches `scores.npz`. `Setup(name)` bundles member, validation and test-pool scores and hashes.
  - Names ending in `_flow` (`caida_flow`, `mawi2020_flow`) are real traces. Keys are (src, dst, proto) flows; UDP flows are members. `load_flow_trace(setup)` returns the time-ordered query stream, and experiment scripts treat these as a single workload named `真实轨迹`.
- **Allocation.** `allocate()` gives each PLBF score segment one kind: PASS (direct pass, i.e. FPR 1), BF, AQF or EMPTY. It does this by Lagrangian bisection followed by a greedy fill.
- **Budget accounting.** `Structure(...)` builds the filter and charges model bytes (`n_trees × 700`), any cache share (`cache_frac`) and the filters against the budget. The `free_cache=True` option gives the infinite-cache lower bound.
  - BF probe positions come from independent hashing (`bf_pos`). Double hashing was a real bug: it badly inflated FPR in tiny segments with many bits per member.
- **Simulation.** Simulators are numba `@njit(cache=True)` loops:
  - `common.simulate`: general, with AQF adaptation and a FIFO cache;
  - `exp4.simulate_policy`: static FP set with FIFO/LRU/oracle-LFU/OPT caches; LRU is the default since exp4;
  - `exp6.simulate_split`;
  - `exp9.run_controller`: the monotone online controller, with `damp`/`thresh`/`init_cap` options.

  Numba does not bounds-check. Mixing uint64 and int64 silently promotes to float, so cast explicitly when indexing.
- **Main method, end to end.**
  1. `exp9.fit_stream` turns measured (Q_F, D_F, Space-Saving top-256 mass) into (W, s_F).
  2. `exp9.fp_stream_misses` predicts misses with a Che-LRU model.
  3. `exp12.joint_pick` searches tree count × cache share.
  4. `exp13` runs this on learning-period measurements only. That deployable version is the paper's main result.

## Evaluation conventions (keep these when adding experiments)

- **Shared streams.** Query streams come from `exp2_repetition_cache.make_stream(spec, n_pool, np.random.default_rng(2000 + seed), score_order)` with workloads from `workloads(pools)`. Every experiment sees identical streams, so rows from different experiments can be merged and compared per (dataset, budget, workload, seed).
- **Fair window.** From exp10 on, the first 25% of each stream is a shared learning/warm-up period and only the last 75% is scored. Cache methods compute this as FP(full stream) − FP(first 25%).
- **Cost metrics.** Relative cost is measured against the best method or grid point for that workload, with +1-false-positive smoothing. High-budget settings (★, ≥8 bits/member, listed in `exp12.HIGH`) must be read in absolute FPs per million queries, because FPRs there are ~0.
- **Adding an experiment.**
  - Number it `src/expN_<name>.py` with outputs in `results/expN_<name>/` (`rows*.json`, `report.md`, `结论.md`).
  - Continue the figure numbering.
  - Append a dated section to `docs/决策记录.md`.
  - Add budgets for new datasets to `exp9.SETTINGS` / `exp12.HIGH`.

## Operational gotchas on this Mac

- **Background runs.** Launch long runs through the harness's background runner, with a parent shell that `wait`s, wrapped in `caffeinate -s -i`. A process left orphaned with `&` after the shell exits gets throttled to efficiency cores (5–10× slower), and lid-closed sleep pauses jobs.
- **Waiting on jobs.** Poll for result files. Never use `until ! pgrep -f "<pattern>"`: the waiting loop's own command line matches the pattern, so it never exits.
- **Memory.** Caida-sized processes use ~2.5 GB each. Running many in parallel has triggered memory-pressure kills.
- **MAWI downloads** (`mawi.wide.ad.jp`) are heavily throttled after the first few MB. Fetch a byte range with `curl -r`, then decompress to a file. `tcpdump -r -` from a pipe does not work here.
- **MAWI packet lengths.** `prepare_mawi.py` converts tcpdump payload length to IP total length, to match Caida's semantics (payload length leaks the protocol through 0-byte ACKs).
