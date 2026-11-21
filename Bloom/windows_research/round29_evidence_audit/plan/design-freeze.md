# Round29: existing evidence, dataset-cluster uncertainty and resource accounting

2026-11-21. Analysis only: no new model selection, no rerun of cancelled round21, no paper edits. Source paper version e256658:vldb/sections/experiments.tex.

## Fixed statistical analysis

Input: round19 updated_main_comparisons.csv. Preserve original main cohort, probe exclusion and reference>=30 eligibility exactly (748cases/cache format). Keep old and GT19-repaired counts side by side. Reproduce original21(dataset*workload-group) clusters and their two-sided Wilcoxon test as historical diagnostic; do not try alternative grouping to minimize p.

Primary uncertainty add-on: resample the8whole datasets with replacement50000times, seed2901. Carry all within-dataset clusters together. For each resample retain the original equal21-cluster estimand by sum(cluster log ratios)/count(clusters), then exponentiate. Report percentile95%interval and small-cluster caveat. Prespecified sensitivity: equal weight to8dataset-level cluster means, with percentile and t(7) intervals; this has a different estimand, not a preferred result selected after significance. Dataset rows give descriptive paired effect and cluster count, not invented single-dataset confidence intervals. No equivalence/noninferiority claim without a margin/prospective design. Same-format Replay comparator for index and fp64; do not mix the old indexed eligibility reference with fp64 effect denominator.

## Resource evidence

Create one actual selected-RA6 physical breakdown per original dataset/budget/cache format using the first seed0 uniform-10k setting (static classification datasets) or original real-trace row. These are explicitly historical frozen RA6 rows, NOT newly rebuilt/repaired configurations; these particular rows are unaffected by the round19 count-gap repair. Charge model payload, BF payload, navigation metadata, ndarray/dict overhead and allocated CLOCK array; assert sum==total<=budget. List backend sorted member-hash payload8*n and one owning ndarray header separately (index scenario), versus no verification index in fingerprint scenario. Backend full records/key storage and transient training/counters/scores not in deployed filter budget; not measured as zero memory. Build-time index creation and safe-prefix computation are not free when backend lacks an existing index.

Correctness audit: verified-prefix may insert only after definitive nonmembership feedback and only when a stored prefix excludes ALL member hashes; hash collisions or required length>P cause bypass, not unsafe insertion. Model/route changes or member updates require coordinated rebuild/invalidation. fp64 collision guarantee is probabilistic under ideal, non-adversarial hashing, union bound min(1,S/2^64) per member query for at mostSresident negative fingerprints. Lifetime/adaptive/adversarial guarantees do not follow. Report occupied-slot bound, not a universal fixed2.4e-15 number. Collision-injection unit test must show prefix bypass preserves member and fp64 can reject it; a synthetic representational collision is not a discovered real hash collision.

## Zero-tree evidence

Revalidate round17 and round20 archives and synthesize, do not silently rerun or replace RA6. Predictive RA6-Z versus exact-learning ZGate are distinct variants. Report all192cases each with weak TCP, strong model and fresh controls; retain26future regressions against repaired RA6 and additional learning-replay cost. Both expanded candidate variants alter original no-repeat-to-Gama property. The cancelled shared-replay round21 remains cancelled and is not a completed timing result.
