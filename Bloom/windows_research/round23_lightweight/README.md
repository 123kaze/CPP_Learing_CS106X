# Lightweight scorer screening (separate experiment branch)

First isolate whether a cheaper scoring model is useful before changing cache predictors or learning objectives. Two existing datasets(URL and CAIDA TCP-only), two budgets each; pureBF, LR, GaussianNB, Additive16, MLP8, Tree1 and Tree16. No negative cache or PCA in this first comparison. Original train/validation/test split preserved.

Six independent single-threaded processes,36 fresh model trainings and84 physically budgeted static-filter records. Three repeated100K native-loop timings per fitted instance; these are batch-amortized microbenchmarks, not database or Python scalar-API latency. Preprocessing parameters, model arrays and required layout headers count against the filter budget. Nonconverged optimization status is retained.

```bash
../../.condaenv/bin/python src/test23.py
caffeinate -s -i ../../.condaenv/bin/python -u src/run23.py
```

See plan/design-freeze.md. Source files and old results are not changed. User's new cost-weighting/feature-cell routing proposal will be considered separately, not mixed into this frozen comparison.
