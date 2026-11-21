# Artificial backend-cost sensitivity: predictions versus measurements

**Complete:**288timings,8fixed settings,6prespecified extra-cost levels,2methods,3repetitions. Every insertion follows real SQLiteNonefeedback; artificial waiting is added to EVERYactualSQLresponse, including members. No wait on filter rejects/cache hits. All288masks,FPcounts and finalCache states match round31.

These are real total-time measurements of local SQLite PLUS an artificial CPU busy-wait service-cost adapter. They are NOT measurements of a real remote database, network latency, cold storage, larger member set, or concurrent service. Python/scalar dispatch and adapter overhead are included.

## Predicted and observed wins (RA faster than BF+Cache)

| Extra cost/SQLcall(us) | Prior round31forecast | Contemporary0uscalibration forecast | Observed median wins | Wins in all3paired repetitions |
|---:|---:|---:|---:|---:|
| 0 | 0/8 | 0/8 | 0/8 | 0/8 |
| 5 | 1/8 | 0/8 | 0/8 | 0/8 |
| 10 | 2/8 | 1/8 | 1/8 | 1/8 |
| 25 | 3/8 | 3/8 | 3/8 | 3/8 |
| 50 | 6/8 | 5/8 | 5/8 | 5/8 |
| 100 | 7/8 | 7/8 | 6/8 | 6/8 |

## Full paired curve

| Setting | Extraus | RA us/query | BF+Cache us/query | Observed ratio | Prior forecast ratio | Current0forecast ratio | Paired wins/3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| cod | 0 | 7.8281 | 2.1930 | 3.5696 | 3.3406 | 3.5696 | 0/3 |
| cod | 5 | 8.5441 | 3.3514 | 2.5494 | 2.2013 | 2.5864 | 0/3 |
| cod | 10 | 8.6705 | 4.3306 | 2.0022 | 1.7111 | 2.0780 | 0/3 |
| cod | 25 | 10.2203 | 7.4281 | 1.3759 | 1.1440 | 1.4069 | 0/3 |
| cod | 50 | 12.6979 | 12.6616 | 1.0029 | 0.8558 | 1.0254 | 1/3 |
| cod | 100 | 17.6468 | 22.9910 | 0.7675 | 0.6813 | 0.7793 | 3/3 |
| url | 0 | 3.0018 | 1.4389 | 2.0862 | 2.0026 | 2.0862 | 0/3 |
| url | 5 | 3.5558 | 2.2169 | 1.6040 | 1.5078 | 1.6583 | 0/3 |
| url | 10 | 4.0626 | 2.8694 | 1.4158 | 1.2911 | 1.4364 | 0/3 |
| url | 25 | 5.6195 | 4.9148 | 1.1434 | 1.0375 | 1.1429 | 0/3 |
| url | 50 | 8.0478 | 8.3196 | 0.9673 | 0.9073 | 0.9758 | 3/3 |
| url | 100 | 13.0538 | 15.0532 | 0.8672 | 0.8282 | 0.8678 | 3/3 |
| caida | 0 | 6.3673 | 2.9506 | 2.1580 | 2.0854 | 2.1580 | 0/3 |
| caida | 5 | 7.1712 | 4.8340 | 1.4835 | 1.3206 | 1.5200 | 0/3 |
| caida | 10 | 7.6632 | 6.4623 | 1.1858 | 1.0195 | 1.2117 | 0/3 |
| caida | 25 | 8.9368 | 11.3080 | 0.7903 | 0.6898 | 0.8255 | 3/3 |
| caida | 50 | 11.7543 | 19.2556 | 0.6104 | 0.5294 | 0.6156 | 3/3 |
| caida | 100 | 16.9856 | 35.0497 | 0.4846 | 0.4345 | 0.4838 | 3/3 |
| shalla | 0 | 2.9846 | 2.0728 | 1.4399 | 1.3680 | 1.4399 | 0/3 |
| shalla | 5 | 3.6461 | 3.2702 | 1.1149 | 1.0700 | 1.1679 | 0/3 |
| shalla | 10 | 4.2522 | 4.1960 | 1.0134 | 0.9378 | 1.0284 | 0/3 |
| shalla | 25 | 5.9778 | 7.2623 | 0.8231 | 0.7818 | 0.8454 | 3/3 |
| shalla | 50 | 8.9762 | 12.2335 | 0.7337 | 0.7012 | 0.7420 | 3/3 |
| shalla | 100 | 14.8500 | 22.1119 | 0.6716 | 0.6520 | 0.6754 | 3/3 |
| caida_flow | 0 | 2.6618 | 2.2396 | 1.1885 | 1.2107 | 1.1885 | 0/3 |
| caida_flow | 5 | 3.8062 | 3.7284 | 1.0209 | 0.9846 | 1.0098 | 0/3 |
| caida_flow | 10 | 4.6745 | 5.1793 | 0.9025 | 0.8974 | 0.9270 | 3/3 |
| caida_flow | 25 | 7.4217 | 9.0989 | 0.8157 | 0.8033 | 0.8263 | 3/3 |
| caida_flow | 50 | 12.1031 | 15.5042 | 0.7806 | 0.7579 | 0.7729 | 3/3 |
| caida_flow | 100 | 21.2129 | 28.5487 | 0.7430 | 0.7312 | 0.7399 | 3/3 |
| mawi2020_flow | 0 | 2.1061 | 1.2902 | 1.6324 | 1.6541 | 1.6324 | 0/3 |
| mawi2020_flow | 5 | 2.6949 | 2.0033 | 1.3452 | 1.3167 | 1.3582 | 0/3 |
| mawi2020_flow | 10 | 3.2371 | 2.6699 | 1.2124 | 1.1709 | 1.2203 | 0/3 |
| mawi2020_flow | 25 | 4.7530 | 4.5751 | 1.0389 | 1.0018 | 1.0422 | 0/3 |
| mawi2020_flow | 50 | 7.3200 | 7.8159 | 0.9366 | 0.9157 | 0.9429 | 3/3 |
| mawi2020_flow | 100 | 12.4848 | 14.2561 | 0.8758 | 0.8635 | 0.8796 | 3/3 |
| mawi2021_flow | 0 | 2.0886 | 1.1591 | 1.8020 | 1.7164 | 1.8020 | 0/3 |
| mawi2021_flow | 5 | 2.6822 | 1.7850 | 1.5026 | 1.3888 | 1.5130 | 0/3 |
| mawi2021_flow | 10 | 3.1853 | 2.3662 | 1.3462 | 1.2513 | 1.3660 | 0/3 |
| mawi2021_flow | 25 | 4.7545 | 4.0572 | 1.1719 | 1.0947 | 1.1746 | 0/3 |
| mawi2021_flow | 50 | 7.3303 | 6.8634 | 1.0680 | 1.0161 | 1.0670 | 0/3 |
| mawi2021_flow | 100 | 12.5152 | 12.5039 | 1.0009 | 0.9689 | 0.9981 | 2/3 |
| mawi2022_flow | 0 | 2.1410 | 1.1482 | 1.8646 | 1.7727 | 1.8646 | 0/3 |
| mawi2022_flow | 5 | 2.6601 | 1.7964 | 1.4808 | 1.4333 | 1.5613 | 0/3 |
| mawi2022_flow | 10 | 3.2276 | 2.3503 | 1.3733 | 1.2915 | 1.4085 | 0/3 |
| mawi2022_flow | 25 | 4.8687 | 4.0824 | 1.1926 | 1.1304 | 1.2111 | 0/3 |
| mawi2022_flow | 50 | 7.5862 | 6.9278 | 1.0950 | 1.0497 | 1.1008 | 0/3 |
| mawi2022_flow | 100 | 12.9369 | 12.6343 | 1.0240 | 1.0013 | 1.0305 | 0/3 |

## Model check and limits

- With only the contemporary0usintercept calibrated, median absolute residual across the80positive-delay method/setting points is0.134849us/query; maximum is0.529637us/query. Individual residuals and requested/observed busy-wait costs are retained in curve_points.csv and timings.csv.
- The round31forecast was saved before any new timing. The current0forecast changes only the intercept to this campaign’s0usmeasurement; slopes remain actual backend-call proportions. No fitting to the positive-delay observations or after-the-factdelay-grid extension.
- Measured_median_wins uses the ratio of method medians; median paired ratios and each repetition’s direction are separately retained. Three repeated timings of the same stream are not independent datasets or a significance test. Near1ratios and inconsistent paired directions should not be called stable improvements.
- Additional service cost can make avoided backend calls pay for the model in this controlled setup. It does not prove such costs occur on a particular real backend, nor that this fixed selector is latency-optimal.
- Actual busy-wait spans can overshoot; the total timer also includes clock checks and adapter bookkeeping. Database/CPU cache state, method order and scheduling can make the linear-cost model imperfect. The counts and cache semantics, however, are checked invariant for everyrun.
- Increasing queryNalone cannot turn an existing loss into a win while per-query costs and fixed costs remain unchanged:the difference is affine with positive slope. Changing the working set, repetition, member count or BFload violates that assumption and needs a separate experiment.
- Round31COD has3000000members and159182848database page bytes (~53.060949B/member). Linear extrapolation of file size is not a critical member-count prediction; neither activeworking-set size nor unchanged FP/Cachebehavior follows from a larger file.
- Do not substitute these artificial-cost rows for the original real-backend rows, and do not claim real remote production performance. No manuscript edit was made.
