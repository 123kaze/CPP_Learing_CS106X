# Figure data manifest

All plotted values are actual experiment outputs. Backend-latency panels are explicitly projections from measured CPU time and backend access counts, not measured disk latency. No mock data are used. PNG450dpi and SVG are exported; English labels avoid platform-dependent Chinese font substitution.

|Figure|Data|Source|Script|Outputs|
|---|---|---|---|---|
|Causal trace FPR|data/causal_trace_fpr.csv|results/main/*_flow/*.json; one trace, no confidence intervals|src/make_figures.py|causal_trace_fpr.png/.svg|
|Model vs grid FP|data/model_grid_fp.csv|results/main for four scalar/URL datasets; fixed workload seeds; +1 only for log display|src/make_figures.py|model_grid_fp.png/.svg|
|Measured CPU projections and actual KV|data/projected_speedup.csv; data/sqlite_latency.csv|results/live/*.json and results/sqlite_backend.json|src/make_figures.py|end_to_end.png/.svg|

The scatter and box distributions are descriptive across declared scenarios, not independent statistical replications. Inferential outputs are in tables/paired_comparisons.csv.
