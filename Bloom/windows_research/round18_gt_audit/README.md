# Round18: read-only audit of the frozen frequency estimator

**Complete: all 1,146 original cases + 4 MAWI-24 budgets; a separate 16-case TCP-only supplement. No method repaired or rerun.**

[English report](results/report.md) · [中文结论](results/结论.md) · [Affected 14 cases](results/affected_cases.json) · [Full case table](results/cases.csv)

The scanner regenerates actual frozen learning streams and verifies their full-base hashes against archived round13 records. It uses each dataset's actual negative pool, not a common approximate pool size. The 1,150 original/holdout budget cases correspond to 325 dataset/workload/seed groups.

## Findings

- **14 repeated-key main cases** have a missing-next-bin trigger: four uniform-100K streams, each with exactly one key seen five times and no key seen six times. That is five of 2.5M learning queries, or 0.0002%, per stream.
- **140 all-singleton main cases** also satisfy the literal trigger but belong to the original no-repeat construction. Unconditional fallback would assign seen mass1 plus unseen mass1; these cannot be treated like the repeated-key failure.
- Original four flow traces, MAWI-24 and all four TCP-only traces have **no** missing-next-bin trigger for c<=5.
- None of the archived actual learning streams has total seen+unseen mass collapse. Constructed equal2–5-repeat inputs do reproduce that defect.
- A diagnostic fallback that preserves the all-singleton case leaves rate arrays byte-identical for 1,132/1,146 main cases and all holdout/TCP cases. This is **not an installed fix** or a rerun proving final configuration/FP equality.
- Missing-bin repair and probability-mass calibration are separate: total old mass can differ from1 even without a missing bin, and simple fallback can exceed1. The scan does not decide a repair or submission date.

No model is trained, no candidate reranked, no estimator replaced, and no original FP result overwritten. Counterfactual rates are temporary diagnostic arrays only. All original sources and read input hashes are checked unchanged after each dataset.

## Verify archived diagnostics (standard library, no datasets)

```bash
python3 src/report18.py --verify-only
python3 src/test_report18.py -v
```

This verifies archived arithmetic and source digests, not a fresh regeneration of raw queries. Seven archive tests pass on Python3.10 and the current system Python.

## Re-run the actual-data audit

Requires the existing main environment and prepared original caches. Completed records are checked/skipped; partial logs/outputs are not silently overwritten. Use a separate output copy for a fresh audit, preserving the archive.

```bash
../../.condaenv/bin/python src/test_audit18.py -v
caffeinate -s -i ../../.condaenv/bin/python -u src/run18.py
# Separate TCP-only supplement:
# ../../.condaenv/bin/python src/audit_tcp18.py
```

The scanner uses the frozen counter and generator, never a training or dataset-preparation entry point. The optional next step of repairing and reranking affected cases has **not** been performed. Paper and frozen method files remain unchanged.
