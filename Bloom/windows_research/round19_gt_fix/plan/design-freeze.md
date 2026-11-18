# Round19: minimal repeated-frequency-gap repair

## Scope and provenance

User approved repair A: only for gt=True and2<=c<=5, when N[c]>0 and N[c+1]=0 retain empirical c. Keep c=1, c>5 and gt=False behavior exactly unchanged. No smoothing, normalization, estimator comparison, cutoff tuning, zero-tree policy change or new cache algorithm. Post-freeze repair motivated by a reviewer counterexample; original frozen sources, holdout and all previous results remain historical records.

A new summarize19 function copies the frozen statistic logic with one conditional continue. A scoped context installs ra4.summarize=summarize19 and restores it even on errors. Frozen source hashes are checked before/after. We do not invoke an unsafe generic CLI launcher: old drivers hard-code output paths, skip existing records and/or insist revised results equal old FP. A new thin adapter calls their original selection/evaluation helpers with isolated new outputs. Baseline runs must reproduce archived choices/FP; repaired runs may legitimately differ and are never forced to agree.

The publication branch is based on the user's rewritten origin/main at6fe1922, not stale local main. Deleted round16 content must not be restored or referenced as a new dependency. /tmp/est_cmp.py is not available on this host; externally pasted estimator-comparison numbers are not independently reproduced and are not used to justify estimator superiority. No paper file is edited in this implementation stage.

## Invariants and tests

For identical input: keys/counts/L/N1/state_bytes unchanged; repaired rate>=old rate per key; only observed c in[2,5] with missing next bin changes, to c/L. All-singleton and gt=False statistics byte-identical. Tests include all2/3/4/5 repeats, [1,1,3,3], [2,2,4,4], mixed counts, nonempty next bins, randomized histograms, scoped hook restoration and recovery of nonzero bucket predictions. Non-unit total mass is intentionally not repaired: [1,1,2,2] remains4/3. Do not claim a normalized probability estimator or monotonicity across count classes.

## Actual-data audit before quality rechecks

- Regenerate all325 original dataset/workload/seed groups, matching round18 full-stream and old-rate digests. Verify1146 main cases: exactly14 changed,1132 byte-identical; MAWI-24 four budgets unchanged. No assumption from an approximate common pool size.
- E10 actual learning shares5/10/25/50% over its4 fixed inputs; E11 original three trace prefixes and synthetic hot-swap learning prefix.
- Round8 paper_url/paper_cod once andZipf learning arrays, also used in round13.
- Round7/14 eight real full-construction fixtures, including the local-key compression used by those workers.
- Old E5 learning/key/candidate scaling inputs, deduplicated only when L andpool really match; distinct counts checked against archives.
- Round15 actual1M–100M nested input and separate100K pilot, with stored hashes checked.
- Four TCP-only streams, also used by RA6-Z.
- E4/e789 use the original main25% streams; their statistic-input coverage is explicit. Round12 audit_costs is an archive aggregator, not a new SQLite generator; unrelated functions named summarize are not patched. The old minimal synthetic smoke is not paper performance evidence and is not claimed as newly remeasured here.

Unexpected changed supplementary inputs are explicitly reported as pending follow-up, not silently declared unaffected. No new selection-speed claim: old timing results retain original-version attribution. Complexity of the added branch is unchanged, but wall-clock identity is not asserted.

## Affected original14 cases, both cache formats

COD uniform-100K seed0 at256/1024/4096KiB; URL same seed0 at64/128/256; CAIDA seed2 at128/256/1024/2048; Shalla seed0 at256/1024/2048/4096. Original streams, budgets, cold tails and frozen score/model caches. No retraining is needed to isolate a statistic-only change.

- Indexed RA6 top3/5/10, RA4 and all seven original ablations (including noGT as an unchanged control), and RA6-warm.
- fp64 RA6, same cache format as its original comparison.
- Each selected structure: full FP replay, configuration, byte budget, deterministic reconstructed BF payload, static flags and predicted FP. Original results must match archives; repaired changes are retained.
- Seed0 all-candidate E3 records: recompute original/repaired predictions and build each pair. When full-pool FP flags and cache bytes are identical, deterministic replay on the identical stream permits reuse of the archived measured count, explicitly labeled—not invented as a new timed execution. Otherwise replay the repaired candidate. Original predictions must reproduce archived records within their existing relative tolerance1e-9.
- CAIDA seed2 ranking: validate old top10 against archive, build old/new top10 union and recompute refined predictions/FP. Report changed rankings even when the final winner is unchanged.
- Replay/Gama/BF/Hindsight are not changed by this patch. Their archived sources/input hashes and denominators remain fixed; do not relabel them as freshly remeasured.

## Reporting and safety

Write only round19 outputs. Recompute original-main RA6/reference aggregates and718/748-style counts with changed RA6 rows substituted, compare old/new, and keep prediction/ranking/ablation changes separately. Byte-identical unaffected statistics give a deterministic-input invariance argument, not a claim that1132 filter deployments were executed again. If a revised MAWI result were needed under a broader future fix it would be post-hoc; this local fix verifies no change instead of silently replacing holdout results.

Single-thread, serial. Failure/partial artifacts stop without automatic retry; memory-pressure termination needs user permission before restart. Do not edit frozen code, old result files or the paper. Do not restore the deleted RocksDB publication history.

## Suggested formula wording (not applied to paper)

For observed c>=1, state three branches: raw c for c>5; raw c for2<=c<=5 with N[c+1]=0; min(c,(c+1)N[c+1]/N[c]) otherwise. The cutoff matters: a two-branch formula applying the ratio to c>5 would not match the implementation.

The ratio is related to the classic Good–Turing/Robbins empirical-Bayes construction, but finite-sample histogram ratios, clipping and this fallback do not establish unbiasedness or optimality. Do not claim the patch is Katz's algorithm or that unavailable external synthetic comparisons prove it is best. Boundary discontinuity and nonmonotone adjusted counts remain disclosed.
