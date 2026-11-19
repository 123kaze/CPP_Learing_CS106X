# Round22 v2: KL / Dirichlet / zero-tree diagnostic — complete

[English report](results/report.md) · [中文结论](results/结论.md) · [Scatter](figures/kl_diagnostic.png) · [PDF](figures/kl_diagnostic.pdf)

**13 fixed cases completed. This is not full EB-RA6.** The exploratory `KL-EB22-static13` selector compares four static learned prefixes (1/16/48/96, cache=0, if feasible) using singleton EB mass and capped continuous cost against all 13 zero-tree/cache fractions using frozen GT19/Che predictions. It has no confidence-bound or no-regression guarantee; test-tail outcomes never select the winner.

- Versus exact-learning BF+cache: **9 wins, 2 ties, 2 losses**. All four TCP-only settings choose zero trees; CAIDA/Shalla fresh-adversarial settings still choose worse learned structures.
- Versus RA6-GT19: 6 wins, 7 losses. Learned-cache and some tree prefixes are absent from this restricted diagnostic, so this is not an isolated test of replacing the estimator inside full RA6.
- Same tree/cache=0 EB-vs-h comparisons: 24 improve, 23 worsen; no stable benefit demonstrated.
- Of 141 actual static candidates,35 satisfy the unclipped A identity's conditions;27 satisfy B's two-interior-solution conditions. One raw-KL/capped-proxy gate reversal occurs. Conditional theory is not a deployment guarantee.

The scatter's left panel compares a capped T=0 proxy ratio with actual static/no-cache BF FP. The right panel is **a continuous-model AM/GM versus capped-cost check**, not measured q/r-filter deployment performance. Full point tables are in `results/static_checks.csv`; same-tree comparisons in `results/same_tree_shrinkage.csv`.

## Offline verification

No raw data, model packages or RocksDB required for the report checker:

```bash
python3 src/report22.py --verify-only
python3 src/test_report22.py -v
```

With the existing main environment, 18 small math/control/serialization tests and plotting:

```bash
../../.condaenv/bin/python -I -B src/test22.py
../../.condaenv/bin/python -B src/plot22.py
# On the original experiment host only: re-hash original prepared datasets
# python3 src/report22.py --verify-only --inputs
```

## Provenance and limited publication compatibility

`plan/freeze.json` preserves the exact original-host snapshot, which included more reporting scripts than the runtime imports. The user's rewritten publication history changed one **unused** round17 report prose line. We do not restore that text. `plan/publication-compatibility.json` lists the exact old/new hashes for that reporting-only difference; the archive checker explicitly records when it accepts that variant. No math, selection, cache, worker or protocol hash is exempted.

The frozen experiment launcher still enforces the stricter original-host hash list. A fresh run from the publication copy needs a separate, explicitly recorded rerun protocol rather than silently changing the old freeze. The archived verifier works without that unused original report or raw datasets. Existing completed run directories are never overwritten or silently retried.

The initial `../round22_kl_diagnostic` smoke failed while saving a NumPy scalar to JSON. V2 changes only strict scalar serialization plus its tests; mathematical code, worker, runner and protocol are byte-identical. Failed logs remain. Runtime caches, temporary artifacts and ephemeral runner authorization tickets are not publication inputs and are excluded.

This experiment was explicitly released after the shared-replay campaign was cancelled; that campaign was not restarted. This is one diagnostic pass per case, not a repeated selection-speed benchmark. No paper or previously frozen method was changed.
