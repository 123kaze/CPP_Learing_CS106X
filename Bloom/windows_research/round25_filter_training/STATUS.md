# Complete: matched-capacity training-objective trial

- Six dataset/initialization jobs completed;48 result records, same MLP8 parameter count across branches.
- Five objective/gradient tests passed; actual native scores, all-key filter flags, member acceptance and reload checks passed.
- URL128KiB:all3 initialization seeds improve test FP versus continued BCE (357→325,368→306,457→366).
- URL64KiB:only1/3 improves. TCP learned filters remain worse than pureBF.
- URL continuations hit the fixed100-step budget without convergence; actual function-evaluation/wall costs retained.
- No inference speedup or general dominance claimed; soft-proxy improvement can fail to transfer to the final deployed filter.
- No cache-aware weights, quantization, new model capacity, old source edits or paper changes.
