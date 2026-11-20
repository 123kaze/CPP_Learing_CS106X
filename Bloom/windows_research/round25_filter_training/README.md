# Same MLP8, different training loss: static filter-aware trial

A matched-capacity experiment on branch experiment/lightweight-scorers. Start from the same BCE100 warm model, then compare another100 iterations of BCE against100 iterations of a clipped, physically budgeted static-BF surrogate. Keep the unchanged BCE100 output and pureBF controls.

Two datasets(URL,CAIDA TCP-only),two budgets each,three model-initialization seeds,48 final records. Native MLP/PLBF implementation, parameter count, preprocessing and final validation-driven allocator stay fixed. No cache or quantization yet.

The surrogate uses five soft regions and a legal capped continuous allocation, not raw untruncated KL. Five mathematical/gradient tests pass. Soft-loss improvement does not guarantee hard-deployment improvement; both are measured.

```bash
../../.condaenv/bin/python src/test25.py
caffeinate -s -i ../../.condaenv/bin/python -u src/run25.py
```

See plan/design-freeze.md. No old frozen-code or paper edits, no test-selected checkpoints, no automatic retries.
