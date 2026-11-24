# Round44 report v2: duplicate metadata field repair

2026-11-23. Round44 download, all3qualification workers and9method workers completed. The frozen final report failed before writing tables because `dict(members=..., **diagnostic)` supplied members twice. Error: TypeError: dict() got multiple values for keyword argument 'members'. Preserve original source/report.log/failure.json and all raw results.

This v2 only reads completed original records, verifies their source/input hashes and writes new tables under its own directory. Never execute original parser/selector/timers, never overwrite original outputs. Source and all qualification/data/worker input SHA frozen before v2 output.

Repair: require diagnostic.members == parsed.members, then include the field only once. More generally validate namespace metadata before merging, not hide conflicting values. Tests explicitly check equal and conflicting metadata, all completed rows have zeroFN and equal byte accounting, calculated paired counts agree with underlying records. Original method code/config/FP/stream selection remains unchanged.

Report all3fixed clusters, including weak AUC; use observed number of distinct budgets (cluster-dependent formula) rather than assume9pairs percluster. Report record-order time reversals and sample time span, not a fullweek claim. Preserve task boundary: a constructed prefix-only checkpoint over real requests, not original production backendNotFound. No manuscript edits or push.
