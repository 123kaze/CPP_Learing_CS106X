# SQLite: per-request SQL-confirmed negative feedback

**Completed:**8settings,2backends,3repetitions,312timings. All accepted masks and final packed cache states match the independent batched-label reference. Every online insertion follows an actual SQL result ofNone.

This is a Python scalar API orchestration benchmark with Numba filter probes and real sqlite3 SELECTs. It includes scalar dispatch, feedback, safe-prefix search and result-mask accounting. Features/hashes are prepared outside the timer. It is NOT native-C++ latency, p99, cold disk or network-backend performance. The old batched e789 timing and these online timings are different execution paths; do not interpret their ratio as a hardware-independent slowdown.

## Median time (microseconds/query); every repeat retained

| Dataset | Backend | NoFilter | BF+Cache | Gama | Replay | RA-PLBF | RA/NoFilter | RA/BF+Cache |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| cod | file | 4.039 | 1.546 | 5.402 | 5.206 | 5.166 | 1.279 | 3.341 |
| cod | memory | 0.955 | 0.829 | 4.802 | 4.968 | 4.805 | 5.030 | 5.797 |
| url | file | 3.799 | 1.041 | 1.693 | 2.091 | 2.086 | 0.549 | 2.003 |
| url | memory | 0.795 | 0.595 | 1.358 | 1.746 | 1.719 | 2.162 | 2.890 |
| caida | file | 3.986 | 2.050 | 4.256 | 4.242 | 4.275 | 1.073 | 2.085 |
| caida | memory | 0.928 | 1.002 | 3.855 | 3.820 | 3.810 | 4.105 | 3.803 |
| shalla | file | 4.357 | 1.569 | 2.578 | 2.408 | 2.146 | 0.493 | 1.368 |
| shalla | memory | 1.107 | 0.859 | 2.060 | 1.943 | 1.717 | 1.551 | 1.998 |
| caida_flow | file | 3.708 | 1.626 | 3.017 | 2.002 | 1.968 | 0.531 | 1.211 |
| caida_flow | memory | 0.732 | 0.698 | 1.543 | 1.292 | 1.281 | 1.751 | 1.837 |
| mawi2020_flow | file | 3.512 | 0.970 | 1.801 | 1.640 | 1.604 | 0.457 | 1.654 |
| mawi2020_flow | memory | 0.638 | 0.494 | 1.262 | 1.190 | 1.189 | 1.863 | 2.405 |
| mawi2021_flow | file | 3.410 | 0.810 | 2.151 | 1.458 | 1.390 | 0.408 | 1.716 |
| mawi2021_flow | memory | 0.651 | 0.477 | 1.238 | 1.128 | 1.103 | 1.694 | 2.311 |
| mawi2022_flow | file | 3.391 | 0.813 | 1.680 | 1.470 | 1.441 | 0.425 | 1.773 |
| mawi2022_flow | memory | 0.640 | 0.475 | 1.214 | 1.158 | 1.150 | 1.797 | 2.420 |

## Verification and limits

- RA-PLBF has lower median time in6/16backend-settings versusNoFilter,0/16versusBF+Cache,12/16versusGama. This is descriptive, not a significance claim from16independent datasets.
- Same200000requests as archived e789 in each setting, RNG8member mixing. Learned-method selections, full-tailFP and archived backend-call/member-found counts reproduce. GT19statistics are explicitly identical to the original on these timed inputs.
- Every online run checks the entire backend-call mask and exact packed final cache bytes against a separately labeled simulation. All members are queried through the new compact native path and all negative-pool flags match before timing; final cache member-hit checks are zero.
- FastPLBF48 is infeasible on the four24KiBtraces and is listed as such, not replaced. The complete table includes it and Gama+10%where feasible, even though the compact headline table above has five methods.
- Learned online routing uses4raw-score boundaries instead of legacy1000-segment expanded arrays. All-key equivalence is checked. Actual online model/BF/layout/cache bytes and original conservative reserved bytes are both recorded; no saved metadata bytes are retuned into extraBFbits.
- Backend member-hash index remains external8*nbytes plus header. Safe-prefix computation is inside online feedback timing. Backend database pages, creation/warmup time, prepared-feature memory and peakRSS are distinct from Filter Budget.
- SQLite file mode is warmed and fits local-memory conditions; not cold storage. Methods rotate order over3repetitions; there is no retrospective best-repeat picking. Exact-feedback correctness does not remove all runtime/order/environment effects.
- These results replace neither the frozen FP study nor the originalMAWI24holdout; they are post-hoc execution-path validation. No paper patch is applied automatically.
