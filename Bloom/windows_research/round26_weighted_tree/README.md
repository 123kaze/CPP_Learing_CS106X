# Proposal A: unchanged LightGBM, different negative training weights

**Complete:96 feasible configurations and12 explicitly infeasible; EscapeGT versus Uniform is17 wins /2 ties /13 losses.**

[Full report](results/report.md) · [中文结论](results/结论.md)

Three arms:Uniform, TrafficGT(query-mass weighting), EscapeGT(cache-residual proxy weighting). Fixed model/features/splits; model remains LightGBM. Weighted arms transfer proxy mass from learning keys to disjoint training negatives via a fixed16-tree reference's32 score bins, rather than pretending per-training-key future misses are known.

URL128KiB,CAIDA256KiB,CAIDA TCP32KiB; six tree prefixes up to160, cache0/10%;108 configurations including explicitly infeasible ones. All members and native/BF consistency checked; training, proxy preparation, FP, physical bytes and native timing reported. Full protocol in plan/design-freeze.md.

This is not prior MLP filter-aware training, nor a per-key oracle weighting, nor a full joint model/cache optimizer. Original training identities are unchanged. No claim of new theoretical optimality or predetermined speedup.

```bash
../../.condaenv/bin/python src/test26.py
caffeinate -s -i ../../.condaenv/bin/python -u src/run26.py
```

Failure/partial output stops without automatic retry. At the user's request these experiment records are submitted on the original bloom/submission-baselines branch, not the public ra-gama main.

```bash
python3 src/report26.py --verify-only
```
