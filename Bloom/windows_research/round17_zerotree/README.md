# Round17: RA6-Z with genuine zero-tree candidates

**Complete: 192 cases, 1536 method records; all regressions and native zero-tree checks passed.**

[English report](results/report.md) · [中文结论](results/结论.md) · [Case-level CSV](results/rows.csv) · [Failure-stage diagnosis](results/diagnostics.json)

RA6-Z is a new post-hoc method, not a change to frozen RA6. Thirteen ordinary BF/cache configurations join the predictive candidate table; the global top-five build/refinement rule stays fixed. Plain-BF bytes use the exact round12 representation. When selected, zero-tree deployment needs no model or feature arrays.

## Results, including limitations

| TCP-only cache | Zero-tree chosen | Old RA6/BF+cache median | New RA6-Z/BF+cache median | New win/tie/loss |
|---|---:|---:|---:|---:|
| Indexed | 8/16 | 1.0629 | 1.0084 | 6/2/8 |
| fp64 | 9/16 | 1.0526 | 1.0149 | 6/2/8 |

Ratios use `(FP_method+1)/(FP_reference+1)` per case. Losses against BF+cache fall from 13/16 to 8/16 for each format, but one setting per format regresses versus original RA6. All 80 stronger-model controls remain configuration/FP-identical to RA6; all 80 fresh-adversarial controls also remain unchanged, including the original losses. This does **not** establish that candidate inclusion guarantees a no-regret fallback.

Remaining TCP-only losses are localized to: zero-tree absent from top 5 (5 indexed / 4 fp64), zero-tree built but learned wins refinement (2/2), or zero-tree selected with a different fraction from replay (1/2). No formal result is used to retune the frozen rule.

## Verify archived results without raw datasets

Python 3.10+ standard library:

```bash
python3 src/report17.py --verify-only
python3 src/test_report17.py -v
# On the experiment host, additionally hash all original prepared inputs:
# python3 src/report17.py --verify-only --inputs
```

With the existing main environment:

```bash
../../.condaenv/bin/python src/test_zero17.py -v
```

Seven algorithm/deployment tests and ten archive tests pass. The two original real-data pilots remain separate from the 192 formal cases.

## Implementation and full experiments

- `src/zero17.py`: one-segment BF prediction, union candidate table and frozen-bucket refinement.
- `src/native_zero17.py`: standalone BF-buffer reload, hash-only probes and separate `feedback_absent` admission; no trained model.
- `src/worker17.py`: all eight methods, five archival regressions, full-tail native zero checks.
- `src/run17.py`: serial dataset/cache jobs, frozen source/input verification, failure propagation.
- `plan/design-freeze.md`: exact method rule, cohorts and boundaries.

The runner is resume-oriented. Existing complete results are checked/skipped; partial/error results stop. A fresh campaign needs prepared caches and a separate experiment output copy, not overwriting these results.

```bash
caffeinate -s -i ../../.condaenv/bin/python -u src/run17.py
```

The search still evaluates learned candidates: zero-tree deployment does not mean zero training/scoring cost during search. FP minimization is not latency minimization, and t=0 is not the Direct/no-filter RocksDB option. Indexed-cache safety state and fp64 collision limitations remain. No old frozen code, paper file or dependency environment was changed.
