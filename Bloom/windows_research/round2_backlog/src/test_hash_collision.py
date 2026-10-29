"""Injected prehash collision, not an empirical collision-rate estimate."""
import numpy as np
import engine as E
h=np.uint64(0x123456789abcdef0)
length=int(E.CC.safe_prefix_lengths(np.array([h],np.uint64),np.array([h],np.uint64))[0])
assert length==65
spec=E.F.layout(4096,prefix_bits=64)
def exercise(length):
    slab=E.F.allocate(spec)
    inserted=E.F.insert(slab,h,length,spec['qbits'],spec['rbits'],spec['slot_bits'],4,0,spec['handbits'])
    return inserted,bool(E.F.lookup(slab,h,spec['qbits'],spec['rbits'],spec['slot_bits'],4,0))
verified=exercise(length);unchecked=exercise(64)
assert verified==(0,False) and unchecked==(1,True)
E.save(E.ROOT/'evidence'/'A4-injected-prehash-collision.json',dict(status='passed',safe_length=length,
    verified_inserted=verified[0],verified_member_rejected=verified[1],unchecked_inserted=unchecked[0],unchecked_member_rejected=unchecked[1],
    scope='Two distinct hypothetical original strings deliberately assigned the same 64-bit prehash. Verified cache bypasses; unchecked cache rejects the member. This is not an observed dataset collision or a probability estimate. Scalar64 IDs with bijective hashing cannot produce this collision.'))
print('PASS injected collision: verified bypass; unchecked false negative',flush=True)
