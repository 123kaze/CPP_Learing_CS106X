# Round28: controlled region-repetition mechanism

Date2026-11-21. No edits to frozen rounds or paper. Reference: paper.git origin/main commit e256658, vldb/sections/analysis.tex, Proposition5.3 `prop:gain`, introduced675efec and clarified807860b. The local paper/submission-sync at414d77f is25commits behind and its root sections/analysis.tex is NOT the submission version. Remote references were fetched and the VLDB source read directly without changing the paper working tree.

## Conditional identity

Fix member counts n_i>0, partition, baseline negative mass h_i>0, external cache residence time T, and the same BF bit budget B. Let M_i(T)>0 be cache-resistant request mass, p_i=n_i/sum n, rho_i=M_i/h_i. If BOTH continuous optima are interior (epsilon_i<1), then

F_h/F_M = (sum p_i*rho_i)/exp(sum p_i*log(rho_i)) >=1.

Predicted fractional improvement=1-1/(F_h/F_M). This is an arithmetic/geometric-mean gap, NOT a universal monotonic function of unweighted variance or max/min spread. Under clipping compute capped optima separately; the interior expression is neither blindly claimed exact nor a bound. Coupled finite-capacity CLOCK changes the M_i when BF allocations change, and lies outside the fixed-T identity.

## Frozen controlled design

Use existing URL (fixed16-tree scorer and Gama128KiB partition) and CAIDA TCP-only (fixed1-tree scorer and Gama32KiB partition). Keep these score partitions throughout. No classifier retraining, DP resegmentation, cache share search, winner selection or real-workload claims in this round.

For each partition, hold total negative query probability per region proportional to its frozen smoothed validation h. Inside each region permute key ranks with seed2800, then assign Zipf exponent s_i=1+0.6*a*z_i, z_i evenly spaced[-1,1] over the5ordered regions. a in[-1.5,-1,-.5,0,.5,1,1.5]. Thus ONLY region-specific concentration changes, not aggregate regional traffic, except unavoidable empty-pool regions (explicitly reported and renormalized). This isolates repetition heterogeneity rather than simply increasing traffic in an expensive region. Whole distribution is known by construction; oracle reweighting is NOT a learning-only deployable estimator.

Same per-arm BF bit budgets2 or8 bits per total member, external TTL T1000 or10000 query positions, horizon H300000, stream/BF-hash seeds2801,2802,2803. All filters share each stream and member/negative BF hash salt; common random numbers across parameter settings are paired controls, NOT independent trials. Three allocations: baseline h, the paper's original M_Che(T)=sum[1-exp(-qH)+(qH-1+exp(-qH))*exp(-qT)], and exact discrete-TTL M(T) defined below. The first comparison directly tests Proposition5.3 using the paper's own weights; the exact-TTL comparison isolates the conditional identity from the finite-horizon approximation. Bits floored per region, optimal integer k chosen from adjacent integers. All member recall asserted. Fixed model/threshold/cache metadata cancel between arms; record payload used, unused floor bits and all layout arrays explicitly. These budgets are conditional BF budgets, NOT the128/32KiB full budgets used only to obtain the fixed initial partition.

Use an exactly specified finite-horizon discrete IID renewing-TTL cache for the fixed-T empirical layer. For key probability q and H>T:
M_x(T)=1-(1-q)^T+(H-T)*q*(1-q)^T.
For H<=T: M_x=1-(1-q)^H; T=0 gives Hq. This is the exact expectation of first miss plus renewed TTL misses under the generated IID request stream, and is not silently equated to the paper's finite-horizon Che approximation. Cache occupancy is unconstrained here, so equalT is not equal deployed cache memory. Aggregate M_x by region. Cache insertion follows confirmed-negative static acceptance; TTL hits renew expiration; no cross-key aliases. Continuous conditional identity, independent SLSQP and simulation expectation checks establish this layer.

Also replay the identical two physical BFs through frozen4-way verified-prefix CLOCK with2048bytes per arm. These actual fixed-memory results are a separate outside-conditions panel; no T derived from tail measurements and no joint optimizer. CLOCK must process ALL queries, including static rejects that might alter verified-prefix references. Backend member hash index explicitly outside filter budget. This panel is trace simulation, not backend wall latency.

## Outputs and completion

2datasets*2BFbudgets*7correlations*2TTLs*3seeds=168 paired settings (504physical BF builds; h, paper-Che M, exact-TTL M). Emit h,p,M,rho, bothepsilon arrays, capped conditional improvement, interiorAG prediction and applicability, raw physical TTL/CLOCK FPs, actualBFbytes, staticFPsets/hashes, cache counters, memberFN, all preparation/build/replay time components.

Scatter x=interior formula improvement, y=measured FP improvement. Separate interior TTL, clipped TTL, and CLOCK outside-theorem panels; include y=x reference, distinguish datasets by shape, retain negative outcomes. Zero baseline FP has undefined raw percentage: keep table row, do not draw a misleading smoothed raw percentage. Report +1 ratios separately. Also show algebraic continuous capped result to distinguish implementation discretization/finite-sample noise from a formula failure. No posthoc seed/correlation exclusions or thresholds selected to improve fit. All datasets use existing held-out negative pools but synthetically generated popularity, prominently labeled controlled synthetic traffic on real features.

Freeze sources before formal runs. Unit-test gradient-independent convex solution, TTL exact expectation, static BF recall/physical caps and actual-clock processing. Sequential workers; retain failures; no frozen code edits or automatic retries.
