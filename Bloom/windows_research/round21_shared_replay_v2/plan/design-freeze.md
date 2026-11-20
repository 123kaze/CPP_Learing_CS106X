# Round21 v2: every case, every selector, full selection timing

## User scope change and preserved first version

The user explicitly requested “都要计时” after the first version launched. That process was intentionally stopped, not killed by memory. Its completed/partial records and frozen source remain in ../round21_shared_replay; no old timing is merged into this campaign. The replay kernel itself is imported unchanged from that frozen version. Only benchmark coverage and timing boundaries change.

No new algorithm, KL threshold, unseen-mass shrinkage or desired-speedup tuning. Independent theoretical checking reported conditional A/B identities but counterexamples to the proposed unconditional gate, and is not part of this measured method.

## Coverage:192 x5 x3 =2880 timings

Same entire round20 matrix:32 TCP-only,80 stronger-model controls,80 fresh-adversarial cache-specific cases. All five selectors receive THREE freshly rebuilt selections on EVERY case:
1. RA6: repaired frequency summary plus frozen predictive table/top-five build/refinement.
2. ZGate-serial: original round20 rule, including its actual13 BF candidate builds, early-stopping BF replay and single learned-anchor replay.
3. ZGate-shared: same candidate/choice rule, identical new summary and anchor/all-BF constructions, safe routing and joint replay.
4. Grid-serial: entire learned+13zero grid built freshly, exact original early-stopping selection.
5. Grid-shared: the same full grid built freshly, count/index preparation, same safe routing optimization and joint replay.

No hand-picked timing settings. Application threads=1, all16 dataset/cache jobs serial. Three repetitions occur in the same fresh dataset/cache process, with method order rotated by case/rep/cache. These are independent candidate reconstructions, NOT three independent model trainings or three independent workload seeds.

## Inclusive timing boundary

All methods start with the same resident raw learning stream and already prepared frozen model scores and length-independent per-tree segment arrays. Loading models/data, generating streams, common per-tree segment arrays, JIT warmup and output/verification are outside selection time. This is selection with a fixed trained model, not train-to-ready.

Every timed repetition rebuilds its candidate filters; none reuses a prior repetition's summary, BF flags, cache state, routing mask or winner. RA6 statistics, candidate selection/builds, all BF construction, mapping/routing preparation and replay are included as applicable. Phase fields are diagnostic and the actual outer selection timer is authoritative. The frozen Grid-serial replay includes its own frequency counting in replay_s; Grid-shared records unique/count statistics separately. Garbage collection is explicitly before—not inside—each timer for all methods.

Shared implementations process every routed candidate to completion. Original serial comparators keep incumbent early stopping and no-cache weighted counting. Do not disable serial optimizations or exclude routing overhead to obtain speedup. The common data is identical but candidate sets/quality differ between RA6, ZGate and full Grid; disclose rather than interpret their times as the same optimization objective.

## Exactness outside timers

Before repetitions, freshly construct both candidate sets for the case. Compare complete serial(no-cutoff) replay with safe shared replay: all8 per-candidate counters and each packed CLOCK state byte must agree. State digests/counters are retained as references; heavy candidate arrays are released before timing. For each timed shared repetition, counters and all cache-state digests must again match the full-serial reference. Every timed selector must match its expected complete configuration, total bytes and full static-FP digest.

Preserve the original cross-prefix safety: route observed static positives plus any observed key potentially covered by an insertible static positive's safe prefix within the same bucket. fp64 also routes equal-fingerprint aliases. No static-FP-only shortcut for indexed cache. No-cache weighted-count path follows each original cache module's bypass-counter convention exactly.

Post-choice actual tail evaluation for each reference winner must reproduce archived round20 RA6, ZGate and expandedReplay+Z FP; these are not used to pick any candidate. Timed repetitions must reproduce the identical static flags/configuration, so retained tail equivalence is not relabeled as2880 separately timed service-query runs. Report no query-throughput claim from these selection timers.

Route workspace and all-candidate cache-state payload bytes are recorded; they are not deployed filter bytes. Whole-process RSS includes setup/verification and is not per-method selection peak memory. Learned-score input and the raw trace remain additional work/storage. No claim that the entire process only reads the trace once: only the ordered simulation phase shares one traversal.

## Pilot and preservation

Eight synthetic kernel/state tests passed, including the indexed FP6-vs7 cross-prefix counterexample, fp64 aliases,180 candidates over3 mask words, bucket clipping, uint64 endpoints, unsafe-prefix bypass and no-cache counting. Two new CAIDA TCP16KiB pilots executed all5 selectors x3 repetitions with exact full-grid/guard checks. They are excluded from formal192cases/2880timings. The pilots already show potential slowdowns, particularly full-grid shared replay; no method parameter is adjusted to reverse those outcomes.

Freeze all sources and input references before formal launch. Save all timings and unfavorable results. Reject partial/error artifacts, no automatic retry; memory-pressure failure requires user permission. No old frozen-source or paper edits, no recovered deleted publication directories, no new dependencies. Independent KL reports remain separate.
