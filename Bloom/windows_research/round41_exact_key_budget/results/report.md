# Round41: exact raw-key cache and fair auxiliary memory

This is a new static exact-key variant and a retrospective ClarkNet control, NOT modern production KV evidence. All complete original negative tails and natural mixed tails retained. Timing is replay, NOT service latency.

| Method | 8KiB FP median | 16KiB | 32KiB |
| --- | ---: | ---: | ---: |
| Gama | 27773 | 6619 | 1308 |
| Replay-Exact128 | 14840 | 3790 | 248 |
| RA-global-Exact128 | 15751 | 3790 | 265 |
| RA6-Exact128 | 10853 | 3101 | 234 |
| BF+Exact128 | 8712 | 2410 | 222 |
| PlainBF | 13579 | 6119 | 279 |
| ZGate-Exact128 | 8712 | 2410 | 222 |
| RA6-prefix | 4277 | 1221 | 137 |
| BF+prefix | 3577 | 1231 | 122 |
| PlainBF-envelope | 0 | 0 | 0 |
| BF+Exact128-envelope | 0 | 0 | 0 |
| PlainBF-RAactual | 0 | 0 | 0 |
| DirectHashIndex | 0 | 0 | 0 |

## Paired comparisons

| A / B | wins/ties/losses | median (FP_A+1)/(FP_B+1) |
| --- | --- | ---: |
| RA6-Exact128/BF+Exact128 | 3/0/6 | 1.21136828 |
| RA6-Exact128/Replay-Exact128 | 8/0/1 | 0.88679245 |
| ZGate-Exact128/BF+Exact128 | 0/9/0 | 1.00000000 |
| ZGate-Exact128/RA6-Exact128 | 6/0/3 | 0.82551278 |
| RA6-prefix/PlainBF-RAactual | 0/0/9 | 1222.00000000 |
| RA6-prefix/DirectHashIndex | 0/0/9 | 1222.00000000 |

## Budget and correctness boundaries

Exact128 stores complete raw keys of length<=128; longer keys bypass. Hash only selects a bucket. Byte equality, not fingerprint equality, certifies a hit. The guarantee assumes static membership and truthful exact-backend absence; updates require invalidation. Forced-hash-alias tests must pass. This variant changes cache capacity, so its selection/FP results cannot be attributed to unmodified RA6.

The prefix index is8*n+array-header bytes when required, not free. Envelope baselines get base budget+index; PlainBF-RAactual gets exactly the actual indexed-RA auxiliary total. DirectHashIndex uses the same sorted hashes, rejects only hash absence and still requires exact-backend lookup on hash presence. These controls equalize auxiliary memory, NOT whole-database memory/RSS or placement/latency. A frontend direct index is not interchangeable with a remote backend index.

Exact replay workers hold shared offline inputs and verification arrays, including a member index for separate prefix controls; the exact-cache query primitive itself takes neither an index nor a key-dictionary reference. Input key blobs, traces, model training and NumPy/Python workspaces remain separately charged as preparation/harness, not magically eliminated.

ZGate selects on learning only, tie goes to BF, and pays both searches plus RA replay. No future-tail no-regret, no original no-repeat guarantee, no automatic selection speedup. Long-key bypass is not modeled exactly by the unchanged RA6 heuristic.

All18 original indexed RA/BF regressions pass. Same source log under3seeds×3budgets is not9independent workloads. No significance or universal model-value claim.
