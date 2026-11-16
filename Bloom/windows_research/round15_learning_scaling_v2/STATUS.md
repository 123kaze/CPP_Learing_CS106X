# Complete (2026-11-16)

- Separate 100K correctness pilot: 2/2 successful; canonical RA6 and no-cutoff Replay winner checks passed.
- Formal experiment: 42/42 successful workers; 21 matched pairs across all seven lengths from 1M to 100M.
- Fixed 180 feasible candidates, identical nested input prefixes and shared model/data.
- Source/cache/input-stream hashes and all timing/scan-count arithmetic verified.
- Eight bookkeeping regression tests pass on Python 3.10 and the current system Python.
- English report, Chinese interpretation, individual CSV/JSON and light/dark/linear-axis PNG/PDF figures complete; rendered PNGs visually inspected.
- Measured paired speedup medians increase from 2.24× to 49.24×; no extrapolated timing or new asymptotic-class proof claimed.
- Initial optional-dependency import failure remains in ../round15_learning_scaling; no failed measured repetition was retried.

Paper files and previously frozen sources were not modified. No local TeX installation or compilation.
