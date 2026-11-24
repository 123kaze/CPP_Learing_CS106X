# Source-freeze clarifications (before first parse)

Nominal budgets are ceil(n*{2,4,8}/8192)KiB, min4KiB. If the lower bound/rounding yields identical byte budgets, evaluate each distinct budget once and record actual count; never present duplicate sizes as distinct evidence. This is determined by the formula, not by any inspected data or method result.

Key size changes are counted for transparency; original key_size is NOT a query feature. Timing windows use recorded GET ordinal, not timestamp sorting. Timestamp minimum/maximum and reversal count are explicit; no undocumented claim of uninterrupted sampling. Member directory is exactly the first25%GET distinct key set; later keys are negative for THIS immutable checkpoint even if the original cache/backend contains them.

Full comparison uses actual Exact128 storage and original selector layout adapter from round41; there is no member-hash verification index. Small-scale decoder/first-prefix/split tests precede source freeze; downloaded file contents are not opened before source freeze. Failure after freeze remains failed; no parser patch in place.
