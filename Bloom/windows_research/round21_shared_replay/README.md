> **归档状态：已停止，未完成。** 此版因用户要求扩大计时范围而中止，保留代码和部分结果，不参与后续正式计时汇总。

# Round21: exact shared CLOCK replay

Safe event routing for the unchanged round20 zero-tree guard. Eight synthetic correctness checks and two real pilots passed; formal192-case equivalence and paired timing measurements are now being launched.

Static-FP-only replay is NOT used: indexed-cache routes also include possible cross-key prefix hits, and fp64 routes include equal-fingerprint aliases. Individual counters and complete packed cache states must match frozen full replay. No-cache candidates retain their exact frequency shortcut.

Formal comparisons:
-192 cases /2688 candidate-state pairs against full frozen replay, plus exact round20 winner/tail-count checks.
-16 prespecified gate replay timing settings ×3 alternating-order repetitions.
-4 full-grid controls receive the same optimization, also with3 repetitions; old serial baselines keep early stopping.

Routing preprocessing is inside the shared timer. Models/candidate preparation and replay-workspace sizes are separately recorded; no fresh train-to-ready speedup is presumed.

```bash
../../.condaenv/bin/python src/test_shared21.py -v
caffeinate -s -i ../../.condaenv/bin/python -u src/run21.py
```

Details in `plan/design-freeze.md`. Independent KL/Dirichlet theoretical checks are separate and cannot modify this frozen experimental method. Old sources and paper untouched.
