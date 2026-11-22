# Round41: exact raw-key cache and fair auxiliary-memory controls

2026-11-23. New explicitly labeled variant; no edits to frozen predecessors, no manuscript changes. Protocol and all source/input hashes are frozen before real raw-key extraction or method evaluation. Synthetic tests may run before freeze.

## Questions and limits

1. Can a strict static-membership zero-FN negative cache operate without the 8*n member-hash index? Implement full-key equality, not fp64 equality, and count every allocated cache array byte/header.
2. Compare Gama, Replay, RA-global, RA6, BF+Cache plus Plain BF and a learning-only zero-tree gate, under equal Filter Budget. Preserve all wins/losses; this is not a new independent workload.
3. When an index is NOT pre-existing, compare indexed RA6 with strong baselines allowed its full auxiliary-memory envelope. Also directly query the same sorted member-hash index: hash absence safely rejects; hash equality still goes to the exact backend.

ClarkNet raw logs are already authorized and local, with the round36 stable subset and the round37 seeds/splits. Reconstruct exact GET target bytes (query string retained), verify SHA-derived IDs and features against round36. Do not output raw URL/client data. Whole-log conflict exclusion is retrospective and remains a limitation. This does NOT supply modern prospective production KV evidence.

## Exact cache contract

Single owning uint8 array; 32-byte header; per bucket four fixed slots (128 key bytes + uint16 little-endian length + valid byte + reference byte) and one CLOCK hand byte. Include ndarray header. No retained pointer or ID into a global key dictionary. Hash only selects a bucket using frozen RA6 top32 multiply-shift; a hit requires equal length and all raw bytes equal. Empty keys are representable. Keys longer than128bytes bypass insertion and cannot hit; no truncation, no prefix match. Width fixed before data inspection. Same 4-way CLOCK insertion/eviction semantics; new physical capacity is passed into unchanged RA6 prediction. Model/DP/tree/fraction grids and GT19 remain frozen. Single-process allocation binding is scoped and restored on exceptions; only E5.K is temporarily replaced with the new layout provider, never frozen files.

Only a backend-confirmed absent key is inserted. Static exact backend membership is required; insert/update/delete or snapshot changes require cache invalidation. Hash collisions cannot cause a cache false negative because equality tests full bytes. The BF remains one-sided even under hash collisions. No infinite-lifecycle dynamic guarantee.

## Matrix frozen before evaluation

Seeds3601/3602/3603; Filter Budgets8/16/32KiB; all original14tree prefixes and13cache fractions. Existing 200-tree/31leaf deterministic single-thread model recipe. H=actual tail length for control with round37, not an operational forecast claim.

Exact-key arms: Gama, Replay, RA-global, RA6-Exact128, BF+Exact128, PlainBF, ZGate-Exact128. ZGate compares the RA6 finalist and learning-selected BF candidate by exact learning FP, ties favor BF; charge its additional replay and BF-search cost, don't inherit no-repeat/Gama guarantee or selection speedups.

Indexed arms: frozen RA6 and BF+prefix at base budget (must reproduce round37), plus PlainBF-full and BF+Exact128-full at total ceiling base budget+8*n+ndarray header. Do not optimize learned methods at this enlarged budget or silently omit index cost. An indexed RA candidate without cache requires no index; report its actual per-method total. The large-budget comparators are an envelope baseline, not a claim that they consume identical bytes; additionally build PlainBF at the indexed RA's ACTUAL required auxiliary bytes. DirectHashIndex uses the sorted member-hash array alone, always verifies matching hashes in the backend, so its hash-collision FP is measured, not called an exact-key dictionary. Same static member set. Common backend records and DB indexes excluded symmetrically; this is auxiliary-memory equality, not equal total RSS.

Learning and tail FP evaluated over complete unmodified negative streams, cold tail as round37. Cache sees static-reject queries too. All members must pass static BF; final cache must reject zero members. Exact-key synthetic tests include forced hash aliases and long-key differences. Also replay the natural mixed member/negative tail to check interleaving zero FN and count backend calls, without artificial member resampling. Training/validation negative keys remain excluded exactly as round37; retain original request order.

Timings: raw-key extraction, model training, scoring, GT summary, index build, candidate construction/selection, executable payload checks and full replay separately. These are not feature-extraction+SQLite service latency; a separate subsequent round is required for that claim. Array payload/header deployment ledger is separate from input keys, model training, trace buffers and process RSS.

## Operational limits and records

3 sequential workers, one native thread, no local C++ compilation, no automatic retry. Input raw files remain in their existing isolated directories; parse via Python -I, never execute data. Require2GiB free disk. Per-worker upper bound1200seconds, aggregate3600seconds. Failed partial result/log pairs retained; no restart after kill. Source/input SHA verification before and after, all results and logs retained. No test based on RA winning. Check indexed regression before reporting any new performance conclusion. Source bindings restored even on failure.
