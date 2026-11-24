# Controlled catalogue dataset schema and reproduction

Synthetic, generated locally from frozen code/seeds. No production traffic, external customer keys or externally supplied source data. Seed/suffix/label split generation is explicitly described in [protocol](plan/design-freeze.md). The user authorized controlled construction; positive results must retain this label.

## Catalogue files (locally generated, git-ignored)

`cache/a{0|6}_s{4301|4302|4303}.npz`, six files:

| array | shape / dtype | meaning |
| --- | --- | --- |
| ids | (163840,), uint64 | exact raw keys, unique; top8bits observable namespace, lower56bits random suffix |
| y | (163840,), bool | static exact member truth; used for training/build/reference, never online probe |
| X | (163840,1), float32 | top8bits / float32(255), deterministically derived from raw key |
| member_train | (163840,), bool | seeded random half of65536members |
| neg_train | (163840,), bool | 16384disjoint negative keys |
| neg_val | (163840,), bool | 16384disjoint negative keys |
| neg_test | (163840,), bool | 65536query-pool negative keys |

The ordering of array rows separates build/training cohorts for convenience; **row position is NOT an online feature or key field**. The independent random suffix does not encode cohort membership. The database key is `int(ids[i]).to_bytes(8, 'little')`, not the array index or a hash of a longer string.

`cache/a{a}_s{seed}_{neutral|high_hot|low_hot}.npz`, eighteen files:
- `learn`:250000int64indices into the negative-query pool (NOT into full ids).
- `tail`:750000same-space indices.

Online mixed requests map these negative indices back into full ids; members are inserted at seeded positions for targetp=.1/.9. Each20000query stream is generated identically across methods. These are intentionally synthetic member mixes, not natural positive fractions.

## Deterministic entry points

`src/catalog43.py`:

```python
s, X, hashes, metadata = catalogue(strength=6, seed=4301)
learn, tail, stream_metadata = stream(s, 'high_hot', 4301)
```

These functions only generate data; they do not read existing caches, train a model or inspect methodFP. Set the same NumPy/software versions as[environment](results/environment.json) for byte-level comparisons. Raw array SHA256 values and compressed file SHA256 values are both stored in workerJSON. Compressed-container metadata need not be assumed portable across arbitrary library versions; compare actual raw array hashes as well.

To reconstruct data without overwriting experiment results, import the frozen module using an explicit src path in a Python `-I` script located outside all downloaded-data directories, then write into a new empty output directory. Do not run `run43.py` on an existing result tree: it intentionally rejects overwrites. No downloads are required.

## Exact key vs fingerprint

Hash is SplitMix64(raw_uint64 XOR fixed_salt XOR seed). XOR-shifts are invertible and multipliers are odd modulo2^64; addition/XOR with constants are invertible, so the mapping is bijective on this actual key domain. The frozenfull64cache compares all64hash bits (split into bucket offset+remainder), therefore distinct rawuint64 keys cannot alias to the same cache record. No independent-hash probability bound is needed.

This does NOT justify zeroFN for a generic URL/string compressed to64bits. Input schema correctness matters: if the caller starts from larger keys, the guarantee no longer applies. Static exactbackend absence and cache invalidation on member changes remain necessary.

## What this dataset tests

A deliberately strong distribution separates most positive/negative mass using a tiny model while preserving shared feature support. Repetition concentration is varied independently inside regions while regional query mass is fixed. This lets the experiment distinguish model value, cache value and allocation value, including weak-model/association-direction controls.

It does not prove such a distribution occurs in a particular service, that namespace-based alternative allocators cannot outperform RA, or that online model-training/rebuild costs are recovered in production. The five-method comparison is not an exhaustive survey of all possible namespace-aware filters.
