# Round19: repeated-frequency-gap repair — complete

[Verified English report](results/report.md) · [中文结论](results/结论.md) · [Old/new summary](results/summary.json)

The repaired entry point is `summarize19.summarize19`. It retains empirical c only when gt=True, 2<=c<=5 and N[c+1]=0. Singleton behavior, c>5 and gt=False remain unchanged. Frozen `ra4.py` is preserved for historical reproducibility; old drivers do not automatically become repaired drivers.

Use `entry19.patched()` in a fresh process to install the shared-module function temporarily and restore it on exit/error. The round19 adapter calls frozen selection/evaluation functions while owning separate output paths; it never overwrites or silently skips original results.

## Verified outcome

- All1,146 main-case statistics checked:1,132 byte-identical,14 affected.
- All4 MAWI-24 budgets and51 supplementary learning inputs unchanged.
- The14 affected cases rechecked in both cache formats, including indexed top3/5/10, warm-cache results, RA4 ablations and candidate predictions/rankings.
- RA6 FP changes in5/14 cases per cache format, with both improvements and regressions. Across168 selected RA-family comparisons,51 FP counts change. Do not claim all results are unchanged.
- Against BF+cache, the748 eligible main cases remain718 wins/0 ties/30 losses in each format, with unchanged median ratios. Same-format Replay aggregate ratios change slightly; see the full precision summary.
- This is a local post-freeze repair, not a normalized or monotone estimator. No claim of finite-sample unbiasedness, optimality or superiority over other estimators is established. Boundary discontinuity and non-unit total mass remain disclosed.

## Verification

```bash
# Python3.10+ standard library; no original datasets needed:
python3 src/report19.py --verify-only
# Existing main environment:
../../.condaenv/bin/python src/test_summarize19.py -v
# Experiment host only: additionally hash original data and reference files
# python3 src/report19.py --verify-only --inputs
```

Fourteen unit/invariant/integration tests pass. Archived unchanged cases are justified by identical statistics and remaining inputs, not relabeled as newly executed filters. E3 measured counts are reused only when full-pool flags/cache/stream are identical, explicitly labeled; changed candidates are replayed.

`run19.py` is resume-oriented, not a fresh-rerun command for an archive containing completed results. Use a separate output copy for a new campaign. Original timing results keep their original-version attribution. Paper edits and statistical-significance recomputation are not performed here. The user's removed publication content is not restored.
