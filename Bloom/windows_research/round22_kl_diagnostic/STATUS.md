# Stopped: serialization failure in URL smoke

The only smoke worker failed while serializing a NumPy boolean in its result. No complete candidate result was saved; remaining matrix never started. This is not a memory failure or evidence about algorithm performance. Frozen source/logs remain; v2 only repairs strict JSON scalar encoding and adds regression checks.
