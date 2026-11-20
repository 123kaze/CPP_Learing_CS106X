# Complete: first lightweight scorer screen

- Branch:experiment/lightweight-scorers. Two real prepared datasets, two budgets, six models+pureBF.
-36 fresh model trainings and84 filter records completed;5 synthetic gradient/native/byte-accounting tests passed.
- Native scoring agrees with fitted reference models; native BF outputs and serialization round trips agree; no member rejection or budget overrun.
- URL small MLP offers lower inference/storage cost than16 trees at higher FP. URL additive/MLP optimization did not converge within fixed100 iterations, retained as such.
- TCP-only all learned alternatives remain worse than plainBF in this fixed-feature static test.
- No cache-aware training, raw feature change or paper modification. Follow-on direct-cell experiment is separate.
