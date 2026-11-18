# Complete: feature implemented, weak-model gap partially reduced

- 192/192 cases, 1536 method rows and 16/16 dataset/cache jobs completed successfully.
- Indexed TCP-only chooses zero-tree in 8/16 settings; fp64 in 9/16. Each reduces BF+cache losses from 13/16 to 8/16, not to zero.
- One regression versus original RA6 per cache format is retained. Stronger-model 80 cases and fresh-adversarial 80 cases remain configuration/FP-identical to original RA6; adversarial losses are not fixed.
- All five original references reproduce round13. All selected zero-tree variants pass physical bytes, full-tail native BF/CLOCK equality and member checks.
- 7 unit tests and 10 data-free archive tests pass. Original source/input digests and complete report arithmetic checked.
- Reports include every remaining failure and whether zero-tree was pruned, lost refinement, or chose another cache fraction.

No oracle gate, threshold retuning, forced fallback or paper modification was introduced after seeing results. The original frozen RA6 remains unchanged.
