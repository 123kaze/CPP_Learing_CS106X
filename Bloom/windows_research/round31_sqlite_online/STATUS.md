# Round31: COMPLETE AND VERIFIED

2026-11-22: all8sequential fresh-process workers completed.4unit tests passed before freeze; report31.py independently verified312timing records across52feasible setting/method combinations, twoSQLite backends and3repetitions. Four trace settings explicitly record FastPLBF48 infeasibility.

Evidence: results/completion.json and results/verification.json. Every accepted-request mask, final packed cache, member check and planned repetition passed. No result was excluded for poor timing. Median RA time beats NoFilter in6/16backend-settings, Gama in12/16, BF+Cache in0/16. Raw timings and all losses are retained.

The live online driver receives no membership-label array. Cache insertion occurs only after its actual SQL result isNone. The old label-driven batch path is separately labeled correctness-reference code, not the online path.

No paper patch has been applied; the user requested experiments and chose patch-only for manuscript changes.
