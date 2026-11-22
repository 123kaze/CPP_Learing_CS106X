# Independent-process SQLite over local TCP

**Completed:**8settings ×3methods ×3repetitions=72formal timings, after6prespecified pilot rows passed. No artificial waiting or network delay was added. The server is a separate process bound only to127.0.0.1; this is NOT a cross-machine or production Redis/PostgreSQL benchmark.

The server performs an actual SQL lookup for every request. Only an absent result for GET_WITH_PREFIX triggers its backend-owned safety index. NoFilter uses plainGET and is not charged unnecessary prefix work. The live client uses only the actual TCP response; its Filter object contains neither labels nor the full member index.

| Dataset | KiB | NoFilter us/query | BF+Cache | RA-PLBF | RA/BF | RA/NoFilter | RA faster in paired reps |
|---|---:|---:|---:|---:|---:|---:|---:|
| cod | 1024 | 37.1893 | 8.9527 | 9.1350 | 1.02036 | 0.24563 | 1/3 |
| url | 128 | 36.8069 | 5.9274 | 5.8472 | 0.98647 | 0.15886 | 3/3 |
| caida | 256 | 36.5590 | 13.2398 | 8.1626 | 0.61652 | 0.22327 | 3/3 |
| shalla | 1024 | 37.0477 | 8.4120 | 6.4703 | 0.76918 | 0.17465 | 3/3 |
| caida_flow | 24 | 36.6122 | 10.9315 | 8.6767 | 0.79373 | 0.23699 | 3/3 |
| mawi2020_flow | 24 | 36.6097 | 5.5246 | 5.3044 | 0.96013 | 0.14489 | 3/3 |
| mawi2021_flow | 24 | 35.9606 | 4.7606 | 5.0784 | 1.06675 | 0.14122 | 0/3 |
| mawi2022_flow | 24 | 36.1137 | 4.7366 | 5.4036 | 1.14082 | 0.14963 | 0/3 |

RAhas lower median query time than BF+Cache in5/8settings and NoFilter in8/8; it is faster than BF+Cache in all3paired repetitions in5/8settings. These are repeated measurements of fixed streams, not independent-sample significance tests.

## Correctness and measurement scope

- All72complete accepted masks,FP counts and final packed caches match the original reference. Server SQL/found/absent/prefix counters independently agree with client counts. All finite member checks are0FN.
- BothTCP endpoints useTCP_NODELAY; one persistent connection and one outstanding request, no batching or concurrency-throughput claim. Application request/reply byte counts excludeTCP/IPheaders. Main timing is full-streamwall/N, not per-queryp50/p99.
- Prefix computation is physically on the server after SQLNone; full index payload8*n andarray header are separately listed. The client verification harness retains its own offline reference data outside the timed path; neither client nor server processRSS is claimed to fit Filter Budget.
- This is a custom SQLite RPC service with an explicit index sidecar, not a capability attributed to unmodified Redis/PostgreSQL. NoFilter/plainGETavoids prefix computation, while both cached methods pay for it when needed.
- Model/feature/hash preparation and DB/index construction are outside query timing and separately recorded. Client and serverCPU andRSS are separately available; serverCPU snapshots include small control/statistics overhead and are not isolated SQL service-time measurements.
- Local loopback introduces real process/serialization/socket overhead but not real remote network hops, TLS, WAN variability, production queues or cold storage. Benefits or failures here cannot fill the cross-machine deployment evidence gap.
- Pilot passed based on correctness and conservative duration/resources, not relative RA wins. Formal methods rotate order and reset only frontend caches; database warm state is documented. All repetitions and losses are retained.
- No paper is modified; the original frozen studies and submission tag are not replaced.
