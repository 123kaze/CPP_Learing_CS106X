"""Correctness-only label reference; never invoked by the online client or server."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'round31_sqlite_online/src'))
from online31 import np,K,J,njit


@njit(cache=True)
def reference_mixed(stream,hashes,member,flags,data,sorted_members,nb,Q,ob,sb,hb):
    counts=np.zeros(4,np.int64);mask=np.zeros(len(stream),np.uint8)
    for i,index in enumerate(stream):
        x=np.int64(index);h=hashes[x]
        if K.lookup(data,h,nb,40,Q,ob,sb,4):counts[3]+=1
        elif flags[x]:
            mask[i]=1;counts[0]+=1
            if member[x]:counts[2]+=1
            else:
                counts[1]+=1;K.insert(data,h,J.safe_len(sorted_members,h),nb,40,Q,ob,sb,4,hb)
    return counts,mask
