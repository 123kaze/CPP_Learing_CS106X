# Round20: explicit zero-tree protection with learning replay

**Complete: 192 cases, 576 live method records.**

[English report](results/report.md) · [中文结论](results/结论.md) · [Run-level rows](results/rows.csv)

RA6-ZGate retains the repaired RA6 winner and the learning-replay winner of 13 physically accounted BF/cache candidates. It chooses the smaller **actual learning FP**; ties prefer zero trees. This prevents predicted top-five pruning from eliminating the entire BF family.

## Results and the precise guarantee

| Cohort, both formats | Cases | Zero-tree selected | Tail vs BF+cache (W/T/L) | Tail vs RA6 (W/T/L) |
|---|---:|---:|---|---|
| TCP-only | 32 | 32 | 0/32/0 | 26/0/6 |
| Stronger-model controls | 80 | 0 | 80/0/0 | 0/80/0 |
| Fresh-adversarial | 80 | 80 | 0/80/0 | 60/0/20 |
| **All** | **192** | **112** | **80/112/0** | **86/80/26** |

The guaranteed equality is `FP_learning(chosen) = min(FP_learning(BF winner), FP_learning(RA6 winner))`. All 192 cases pass. No future-tail data enters the selector. **No losses to BF on this tested matrix is an empirical observation, not a distribution-free guarantee.** All 26 future-tail regressions against RA6 remain reported.

The extra 13 BF candidates and one learned-anchor replay cost real selection time. This new variant does not inherit the old statistics-only49.24× scaling claim, avoid model training during search or represent Direct/no-filter database access. It also does not inherit the original unconditional no-repeat reduction to Gama: the guard may select BF on a no-repeat workload.

## Verify without datasets (Python3.10+ standard library)

```bash
python3 src/report20.py --verify-only
python3 src/test_report20.py -v
# Experiment host: additionally check raw cached inputs
# python3 src/report20.py --verify-only --inputs
```

With the existing main environment:

```bash
../../.condaenv/bin/python src/test_guard20.py -v
```

Eight gate/native-replay tests and nine archival-corruption tests passed. Both pilot formats independently check the empirical objective by exhaustive no-cutoff replay of all 14 final alternatives.

## Full experiments

`src/run20.py` is resume-oriented: completed matching records are skipped, partial/error artifacts stop. Use a separate output copy for fresh measurements rather than overwrite archived results.

```bash
caffeinate -s -i ../../.condaenv/bin/python -u src/run20.py
```

Same complete round17 matrix, repaired round19 statistics, fixed model scores and input streams. Historical predictive RA6-Z/expandedReplay are labeled historical, not new timings. `plan/design-freeze.md` records the rule, scope and inspected original-Gama tree bounds. Old frozen code and paper files remain unchanged. No new dependency is required.
