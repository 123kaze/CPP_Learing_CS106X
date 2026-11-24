# Round43: controlled exact-uint64 catalogue, full predeclared matrix

2026-11-23. User-authorized synthetic data construction. This is NOT a production trace, modern real KV evidence, or an unseen real holdout. Freeze sources before generating full data/models/tails. Tests before freeze use small synthetic fixtures only. No frozen predecessor modifications or manuscript edits.

## Catalogue and feature semantics

Raw key domain is exactly uint64, bijectively encoded as8little-endian bytes in SQLite. Top8bits are a query-visible namespace feature x=bin/255; remaining56bits uniformly random opaque identifier. No numeric ID assigned from membership or query frequency. Resample nothing: if any key duplicate occurs, stop and retain failure. Membership is a random finite catalogue, not a deterministic feature threshold.

For each seed4301/4302/4303, generate65536members,16384negative-training keys,16384negative-validation keys,65536negative-query-pool keys. Negative key sets are disjoint by construction order and uniqueness assert; opaque bytes remain random independent of membership. Member train is seeded random half. Feature-bin distribution: member P(b) proportional exp(a*(b/255-.5)), negative P(b) proportional exp(-a*(b/255-.5)); a in{0,6}. Both distributions have support on every bin: identical feature values can occur in both labels. Record finite support coverage/overlap. Source latent generator is not supplied as a membership oracle; include a bin-presence rule that rejects only bins without any members. If all bins have members, this rule rejects nothing, illustrating lack of a zero-FN feature shortcut.

Features contain only top8bits; not random suffix, true membership, access counts, SQL result or future statistics. Train fixed200tree/31leaf/lr.1 single-thread model on member-train and negative-train. Same14prefixes/13fractions, DP5regions/1000segments, GT19 and frozen RA6 top5. Do not tune model or distribution after seeing tail outcomes. AUC is diagnostic, NOT a continuation gate.

## Request generation

Five equal-width bins of the observable feature (not learned score bins) define controlled regions. In each region, shuffle negative-query keys with fixed seed; assign Zipf ranks with exponent:
- neutral: 1.0 in all five;
- high_hot: .4,.7,1.0,1.3,1.6;
- low_hot: 1.6,1.3,1.0,.7,.4.

Each region's total request probability is EXACTLY its share of distinct negative-pool keys. Thus regional traffic mass is unchanged across correlation arms; only within-region concentration differs. Use common seeded uniform draws through inverse CDF to generate1000000requests, first250000learning, remaining750000tail. No tail-informed reshuffling. Seeded suffix/rank independence prevents model from knowing individual popularity. Populations and associations are explicitly experimental controls, not naturally observed. H=750000 known planned horizon; does not prove robustness to forecasting errors.

## Matrix and baselines

2strengths ×3associations ×3budgets(16/32/64KiB=2/4/8bits per member) ×3seeds =54case keys. Methods Gama, Replay, RA-global, RA6, BF+Cache, PlainBF, ZGate (7 =>378rows). EqualFilter Budget including model/BF/routing/headers/cache. Full64bit cache module stores bijective hash of rawuint64, so is exact for this domain. No member verification index and no S/2^64 probability claim. This special exact-key contract does not fix generic fp64 string compression.

E5.K binding scoped to frozen cache_fp module and restored on exceptions; no file patching. RA6 formula unchanged, only actual layout supplied as in archived round10. All candidates see same learning and tail; Replay uses true cache replay; ZGate compares learning FP of RA finalist and BF-grid winner, tie prefersBF, pays both searches+extra replay. No future no-regret assertion. PlainBF indiv build time measured, not charged all13grid builds.

Also fixed-config weights h/traffic/miss: per case choose validation-minimum predicted FPR anchor at10%cache, fix trees/DPpartition/BFbits/cache/hash, use round37 capped allocation & mass recipe but evaluate full64exact CLOCK. This is a separate diagnostic (162rows), not the mainRA6. Report continuous AMGM/interior conditions and actual CLOCK non-exogenousT; never call the CLOCK comparison a direct proof of the fixedT identity.

## Timings and database comparisons

Per case actual local SQLite raw8byte key queries for NoFilter, BF+Cache, RA6 and Replay. Two synthetic member proportions p=.1/.9, fixed20000total requests each; select random positions for members, remaining positions consume the negative tail prefix in order. Each method sees identical streams, no filtering by observed wins.3repetitions, cyclic method order;54×2×4×3=1296window timings. Raw query decode/hash, feature extraction (top8bit only), model/cache/BF, SQL and absence feedback inside timer. No precomputed features/hashes/labels in online filter. SQLite exact BLOB primary key/32byte values, WITHOUT ROWID, warm local DB/cache2MiB/mmap0, temporary fixture. Input keys/common DB/workspace separate fromFilter Budget. Not remote/concurrent/cold-disk or real-world latency evidence.

Independently label-reference replay with full accepted/found mask + final cache byte checks, allmembers0FN before and after. Allmember/boundary checks outside timer. NoFilter does not decode/hash uselessly. Record source generation/model/score/index-free build/GT/select/verification/SQLfixture/JIT/replay time separately; all native threads1. Compare per-case paired ratios then aggregate, not ratios of column medians. Case families correlated: no independence or statistical-significance claim.

From these measured windows, derive additional-backend-cost crossover C_add=(T_RA-T_B)/calls_saved, only if calls_saved>0. Additional per-call costs0/5/20/100us are projections, NOT busywait or remote measurements. Startup-inclusive extrapolation conditional on stationary rates and sharedlabels; training+sharedscore/GT/select/rebuild costs visible. If RA saves no calls and is slower, expensive backend cannot rescue it; retain this classification.

## Execution safety

Seven+synthetic tests and source freeze first. Fixed pilot: strength0,seed4301,neutral,16KiB with full candidate search/full negative evaluation but2000mixed requests, once each method/p; excluded from formal matrix. Time/RSS gates only: predicted formal<=3600s and RSS<4GiB, >=2GiB free disk; do not gate on AUC/FP/winner. Pilot shared-generation/model setup not multiplied per case; conservative selector/database timing multiplier recorded. Six formal workers (one per strength/seed) sequential, timeout1200each; no automatic retry/kill restart. Every run refuses overwrite, stores failures and all negative results. No new external software/build tool or service. Generated datasets are reproducible by frozen seeds; keep compressed arrays locally ignored, publish hashes/schema/protocol and small synthetic fixtures, not falsely real raw traces.
