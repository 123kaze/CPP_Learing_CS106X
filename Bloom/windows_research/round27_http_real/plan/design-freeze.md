# Round27: real HTTP missing-resource workload — preregistration

Date: 2026-11-21. New experiment; previous rounds and paper untouched.

## Data chosen before inspection

NASA KSC July and August 1995 access logs, Internet Traffic Archive:
https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html
Download the two named gzip files via HTTPS. The archive host's July download timed out after900s (6119090/20676672bytes); an August copy from the public COM6012/ScalableML teaching repository timed out after180s (2149761/16633316bytes). Before any dataset preparation/FP inspection, continue each partial from its SAME URL using4bounded byte ranges per host, validate Content-Range, assembled size and full gzip CRC, and record compressed/uncompressed SHA256. August mirror provenance:https://raw.githubusercontent.com/COM6012/ScalableML/master/Data/NASA_access_log_Aug95.gz (16633316bytes), independently listed with the same size in LinkedInLearning/command-line-data-analysis-4359488. Preserve failed partials, original files locally, SHA256 and provenance. A matching full-file checksum against the unavailable source is not claimed. No host identity analysis, no raw URLs/hosts in published artifacts. These are historical real server workloads, not modern production validation.

Each month is a separate workload, NOT an independent population drawn at random. Parse GET requests only. A resource key is the exact request target bytes (query strings retained; no outcome-dependent canonicalization). Define static catalog from keys with 200 or 304 responses; negatives have 404 responses. Exclude keys having BOTH successful and 404 responses throughout that month, and all other statuses from the stream. This is an explicitly retrospective, static-stable-subset benchmark: catalog construction and conflict exclusion use the whole log. It does NOT claim deployable prediction of resource creation/deletion or live HTTP negative-cache correctness. Report excluded counts and fractions. Host/status/response bytes/frequency/time are forbidden model features.

## Split, features and budgets

Use first 25% of chronological parsed GET records as development/learning time boundary, before filtering by outcome. Training negatives are 10% of key-hash space and validation negatives next10%, ONLY if observed before the boundary. All other negative keys are test-pool keys, including future-unseen negatives. Their real chronological requests in the prefix are learning queries; those after the boundary are evaluation queries. Thus prefix contains approximately, not necessarily exactly, 25% of evaluated negative requests. No tail-dependent downsampling, popularity synthesis or label reassignment. Members: 50% hash-split train, all in BF. Evaluate member recall on all members and report held-out-member/test-negative AUC.

Frozen lexical features: byte length; slash, dot, digit, uppercase, dash, underscore, percent, question, ampersand, equals, tilde counts; max slash-delimited component length; flags trailing slash, .html/.htm, .gif, .jpg/.jpeg, .txt, .cgi, .ps/.pdf (case-insensitive suffix before '?'). No learned vocabulary or external embedding.

Three seed values2701,2702,2703 control key split, BF hash salt and model seed. This is conditional repetition on the same two logs, not six independent workloads. Budget4,8,16KiB, same physical budget for all methods. Full frozen tree-prefix and cache-share grids. A 200-tree LightGBM,31leaves,lr=.1,one thread, deterministic. No per-dataset tuning after seeing FP outcomes.

## Compared methods and measurements

Gama (shared implementation, validation-selected no-cache); Replay (all h-allocated candidates replayed on learning only); RA-global (same h allocation, predicted cache sizing); RA-PLBF (RA6 top5 with explicitly labeled round19 minimal GT repair); BF+Cache (13 pure-BF/cache candidates, learning replay). Optional diagnostic BF without cache is a separately named reference, not an extra selection rule. Old Good–Turing and zero-tree variants are not silently substituted.

Cold evaluation caches, same tail per setting; feedback simulated from stable catalog/nonmembership labels only AFTER static filter acceptance. This is an algorithmic trace replay, NOT real-time backend measurement. Preserve clock ordering; safe-prefix uses all member hashes and may bypass unsafe inserts. No Python label lookup cost presented as backend latency.

Report absolute FP, +1-smoothed paired ratios, model bytes, BF bits, layout/header bytes, cache bytes, used/unused budget, backend member-index payload8*n plus array header, all-member FN, cache occupancy/counters, selected trees/share, prefix/tail sizes/hashes, learning region repeat/hotness and unique-key/traffic region histograms. All training/scoring/index/build/selection/evaluation wall times are recorded; no speedup from isolated one-off timings. No precomputed scoring or route hashes described as native end-to-end query latency.

## Completion and failure policy

Freeze own source and imported research source hashes before formal execution. Unit tests precede it. Formal jobs run sequentially, startup native thread limits set before NumPy import. Atomic result saves, retain errors/partial logs; no implicit retries or changes after freeze. Main table includes all feasible planned budgets, including losses/zero FP; no >=30 filter on this new workload. Diagnose AUC, overlap and repeat heterogeneity without using tail performance to choose a dataset or configuration. If the workload is too small or BF+Cache wins, mark it insufficient as positive evidence rather than change the protocol.
