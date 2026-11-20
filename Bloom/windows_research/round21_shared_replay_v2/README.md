> **归档状态：用户主动取消，结果不完整。** 仅记录735/2880次选择计时（42个已完成任务中的案例，另7个案例来自中断任务）。此前线程配置不符的批次另行排除。这里不是已完成实验或总体加速结论。

# Round21 v2: all-case, all-selector inclusive selection timing

User requested timing everything, not a16-point sample. This version measures all192 cases ×5 selectors ×3 fresh candidate rebuilds = **2880 selection timings**.

Methods: repaired RA6, serial ZGate, shared ZGate, serial full learned+zero Grid, and shared full Grid. Both serial methods retain early stopping; both shared methods include routing preprocessing. All statistics/candidate builds/replay are included as applicable. Prepared model/data and length-independent segment inputs are common and excluded; this is not model-training or service-query timing.

Exactness: all per-candidate FP/hit/insertion/eviction counters and packed CLOCK bytes match full frozen replay. Every timed selection preserves its original configuration and static flags, and reference tail evaluations reproduce round20. Indexed routes include potential cross-prefix state updates, not just static BF positives.

The first subset-timing campaign was deliberately stopped at the user's request. Its frozen code and partial results remain in ../round21_shared_replay; no old timing is reused. The same tested kernel is imported, not edited. Two new full-method pilots passed, with no speedup assumption.

```bash
caffeinate -s -i ../../.condaenv/bin/python -u src/launch_single_thread.py
```

See `plan/design-freeze.md`. Run serially; failed/partial outputs are not automatically retried. No new dependency, paper edit or KL/shrinkage algorithm change.

## Mandatory startup pinning

Use `launch_single_thread.py`, which sets all native thread variables before importing NumPy and asserts OpenBLAS=1 and Numba=1, then execs the unchanged frozen runner. The first v2 launch set variables too late (a separate diagnostic confirmed14 OpenBLAS threads); its files are retained under `results/abandoned_late_thread_environment` and excluded. Prior pilot timings are correctness-only and excluded too. `results/launch_environment.json` records the effective launch state and launcher hash.
