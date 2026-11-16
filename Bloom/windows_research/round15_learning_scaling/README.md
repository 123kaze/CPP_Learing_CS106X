# Round 15: selection-time scaling from 1M to 100M learning queries

Fixed CAIDA/256KiB, original14×13 candidate grid, Zipf1.0, nested learning prefixes and three serial single-threaded repetitions. Frozen RA6 versus exact learned-grid Replay with early stopping. Both include learning preprocessing in selection time; models, scores and L-independent segment arrays are prepared beforehand.

This tests selection-cost scaling, not end-to-end model training or new held-out effectiveness. A growing seconds gap alone does not prove a different asymptotic class; the figure also reports paired speedups. See `plan/design-freeze.md` for the full boundary and sort-based counting caveat.

```bash
# From this directory, with the existing main environment and prepared caches:
caffeinate -s -i ../../.condaenv/bin/python -u src/run15.py
```

Source hashes and the original cache hashes are frozen before launch. The separate100K correctness pilot is excluded. Inputs are generated in1M-row chunks and kept outside Git; no300M tail is allocated. Any failed/partial result stops the runner, without automatic retry.
