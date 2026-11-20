# Direct cell routing: static first test (complete)

[English report](results/report.md) · [Raw result JSON](results/rows.json)

Completed24 deterministic table/filter builds over URL and CAIDA TCP-only, two budgets,16×16/32×32 feature cells, three rebuilds. Only two predetermined features are used(URL len/digits; TCP src/dst). Validation negatives and known members fit smoothed density-ratio order and five-region DP allocation. No cache or residual-cost training.

Two correctness tests pass; all member queries accepted, native routing/BF flags agree with frozen bit querying, and all owning-array memory fits budget. Native lookup is fast but this tiny partition has weak discrimination; TCP still loses to plainBF, URL FP is substantially higher than round23 full-feature classifiers. No retuning after results.

```bash
../../.condaenv/bin/python src/test24.py
python3 src/report24.py
```

A fresh run requires a separate output copy because run24 refuses to overwrite the completed JSON. See plan/design-freeze.md for scope, known literature and why “three bits per cell” is not total router memory. Proposal A(weighted training) and C(raw n-grams) remain distinct follow-up work, not claimed completed here.
