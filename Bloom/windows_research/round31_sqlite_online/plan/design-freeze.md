# Round31: genuinely interleaved SQLite feedback

2026-11-21. New implementation/protocol. Frozen round6 e789 remains unchanged. No paper edits or patch application.

## Purpose

Correct the execution-order mismatch identified in round30. For EACH request, execute cache/model/BF probe, immediately perform SQLite SELECT if accepted, and insert into negative cache ONLY if that actual SELECT returnsNone. The timed online driver receives no membership-label array. No prelabel admission, precomputed staticFP routing or speculative feedback. Features/key hashes may be prepared in advance exactly as in the original microbenchmarks; disclose this is not raw-feature extraction latency.

## Frozen settings

Use all8original e789 settings: COD1024KiB,URL128KiB,CAIDA256KiB,Shalla1024KiB,CAIDA-flow24KiB,MAWI2020/2021/2022-flow24KiB. Same frozen model prefixes, allocator,13cache shares and CLOCK. Read existing prepared models/scores, not retrain. Reproduce original selections and full-pool flags. RA uses GT19 summary and asserts its rate arrays equal the original summary on these specific timed inputs; reject if not equal instead of changing the benchmark. Add physically accounted BF+Cache chosen among13 candidates by learning replay only.

Methods: NoFilter, FastPLBF48, Gama, Gama+10%, Replay, RA-PLBF, BF+Cache. FastPLBF48 is infeasible on the four24KiB traces; explicitly record infeasibility, no substitute. Thus expected52feasible setting/method combinations, two backends, three fresh-cache timing repetitions:312timing records.

Requests exactly follow original e789: first200000negative queries after the25%learning boundary, mix members with probability0.1 using RNG8. Dataset-fixed stream is shared among all methods and database variants. Cache starts empty each execution. Preserve request hash and verify backend-call/member-found counts against the old archived run for learned methods; BF has an independent label-reference check.

## SQLite and timing

Both file-backed and in-memory SQLite, complete member catalog as signed64-bit INTEGER PRIMARY KEY with32-byte BLOB values. Fresh database per setting/backend; database creation not in query timer but explicitly timed. Warm the same member key with2000SQLlookups. This is a warmed file-backed SQLite experiment, NOT cold disk/SSD or network service latency. Record Python/SQLite/Numba versions, rows, page_count/page_size, settings and request hash.

Online query loop is Python orchestrating scalar Numba probes and Python sqlite3 SELECT. Its measured time includes Python/scalar dispatch, SQL calls, result handling, safe-prefix binary search, cache insertion and result-mask recording; do not call it a native C++ latency limit or compare it directly to old batched-native ns/query. No p99 claims, only full-stream wall-time ns/query. NoFilter uses the same SQL driver and accounting but no filter. Preallocate masks; allocations, statistics, cache clearing and correctness checks outside timing. Three repetitions; rotate method order deterministically each repetition, no winner-picked timing. Save every repetition, not just minima.

Original batched label simulation remains a correctness reference ONLY, separately timed as a diagnostic. For each method compare the full accepted-request mask, FP/backend-call/member counts, hits where available, and packed final cache bytes against the actual SQL-feedback path. Member truth can be used ONLY after each online run for assertions and in the separately labeled reference. Check all members against the final cache. Do not use timing outcomes to choose models/caches.

## Deployment and resource scope

Use actual owning model/BF/cache arrays and existing byte-accounted structures. Online learned probing stores only the4raw-score region cuts and the compactuint8 region kinds, not the legacy query harness's1000-segment expanded route/cut arrays. This algebraically equivalent region lookup is checked on every member/pool key and every timed request against the original expanded route. List both original conservative reserved bytes and actual compact online buffer bytes; no saved bytes are reallocated to improve FP after results. Runtime Python object wrappers and request-feature matrices are harness/process memory, not a claim that total RSS fits Filter Budget. Sorted full member-hash index is external backend support,8*n bytes plus header; computing safe length is inside feedback timer. Backend DB pages/records, index creation and peakRSS are separately reported. No database callback uses a membership-label oracle.

## Verification/failure policy

Unit tests before freeze: probe cannot insert; missing SQL result admits, existing row does not; repeat absent request hits only after confirmed insertion; intentional disagreement between fake labels and DB does not affect online feedback; native member recall; identical final cache/mask against independent simulation. Freeze own source and imported algorithms before workers; one fresh worker at a time, native threads1verified beforetiming. Preserve failures and no implicit restarts after memory kills. All repetitions and losses retained. No paper claim of online improvement until the measured result exists.
