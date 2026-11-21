# Frozen failed analysis attempt

2026-11-21. Unit tests3/3passed. First preflight completion-marker path error was fixed before freezing (plan/preflight-failure.json).

After source freeze, the run validated previous archives and computed the fixed cluster analysis in memory, then failed while assembling the resource table: `KeyError: 'model_bytes'`. Round10 fp64 CSVs retain only total/cache bytes and lack the detailed components present in round6 CSVs. No final summary or completion marker was written. This frozen code is retained unchanged.

Continued in round29_evidence_audit_v2 with an explicit, labeled resource reconstruction from the unchanged executable-model layout and archived total. The statistical protocol and code are unchanged. This is a reporting-schema repair, not a new filter experiment or a model-selection change.
