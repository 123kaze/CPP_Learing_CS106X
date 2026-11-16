# Round 15: selection-time scaling from 1M to 100M learning queries

**Complete: 42 successful formal workers, 21 matched input/candidate pairs.**

![Inclusive selection cost and paired speedup](figures/learning_scaling.png)

[English report](results/report.md) · [中文结论](results/结论.md) · [PDF](figures/learning_scaling.pdf) · [Linear axes](figures/learning_scaling_linear.png) · [Run-level CSV](results/timing_rows.csv)

Fixed CAIDA / 256 KiB, original 14×13 grid (180 physically feasible candidates), Zipf 1.0, nested learning prefixes and three serial single-threaded repetitions. Frozen RA6 versus learned-grid Replay with exact early stopping. Both include learning preprocessing in selection time; trained models, scores and L-independent segment arrays are prepared beforehand.

Over 1M–100M queries, RA6's selection median grows from 3.049s to 9.747s; Replay's from 6.867s to 479.965s. Median paired speedup increases across all seven points from 2.24× to 49.24×. Replay retains all optimizations and processes approximately 64–66L ordered candidate query events. The result supports amortizing trace analysis across candidates, not a proof of a different asymptotic class in L at fixed candidate count. See the frozen protocol and the English report for full timing/complexity boundaries.

## Verify archived results without datasets

Python 3.10+ standard library:

```bash
python3 src/report15.py --verify-only
python3 src/test_report15.py -v
```

On the experiment host, `python3 src/report15.py --verify-only --inputs` additionally checks every raw cache and the 100M-query stream. This does not rerun selection.

## Regenerate the figure

```bash
# Requires the existing NumPy/Matplotlib environment, not TeX:
../../.condaenv/bin/python src/plot15.py
```

Light/dark and linear-axis PNG/PDF outputs come from the same complete checked archive. Intervals are min–max of three timing repetitions, not independent-workload confidence intervals. Logs and all measurements, including slower repetitions, are retained.

## Full experiment launcher

```bash
caffeinate -s -i ../../.condaenv/bin/python -u src/run15.py
```

This launcher is resume-oriented: already completed results are checked and skipped; failed or partial results are rejected. Use a separate experiment copy/output location for genuinely new timings rather than overwrite this archive. Source hashes and the original cache hashes are frozen. The separate 100K correctness pilot is excluded. Inputs are generated in 1M-row chunks and kept outside Git; no 300M evaluation tail is allocated.

The initial version in `../round15_learning_scaling` generated the stream but failed on an unavailable optional instrumentation import before any selection measurement. v2 reuses the identical input and changes only thread-check instrumentation; old frozen code and failure logs remain intact.
