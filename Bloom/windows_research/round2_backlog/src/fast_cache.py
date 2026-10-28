"""Word-packed verified-prefix caches, with exact early-stop replay.

Power-of-two quotient buckets are retained. Unallocated reservation bytes are
returned to Bloom storage by the caller; every allocated word/header is charged.
"""
import sys
import numpy as np
from numba import njit
HEAD=4
ARRAY_HEADER=sys.getsizeof(np.empty(0,np.uint64))

def layout(budget_bytes,prefix_bits=40,policy='clock',ways=4):
    assert ways in (2,4,8) and prefix_bits in range(16,65)
    code={'clock':0,'bucket_lru':1,'fifo':2}[policy]
    handbits=int(np.log2(ways))
    best=dict(qbits=0,rbits=0,slot_bits=0,slots=0,buckets=0,nwords=0,
              allocated_bytes=0,budget_bytes=int(budget_bytes),ways=ways,
              policy_code=code,policy=policy,handbits=handbits,prefix_bits=prefix_bits)
    for q in range(1,min(prefix_bits,40)):
        r=prefix_bits-q
        sb=r+7+(64 if code==1 else 1)
        buckets=1<<q;slots=buckets*ways
        words=HEAD+(slots*sb+(buckets*handbits if code!=1 else 0)+63)//64
        allocated=words*8+ARRAY_HEADER
        if allocated>budget_bytes:break
        best.update(qbits=q,rbits=r,slot_bits=sb,slots=slots,buckets=buckets,nwords=words,allocated_bytes=allocated)
    return best

def allocate(spec):
    data=np.zeros(spec['nwords'],np.uint64)
    if spec['nwords']:
        assert sys.getsizeof(data)==spec['allocated_bytes']<=spec['budget_bytes']
        data[1]=np.uint64(spec['qbits']|(spec['rbits']<<8)|(spec['slot_bits']<<16)|(spec['ways']<<24)|(spec['policy_code']<<32))
        data[2]=np.uint64(spec['slots'])
    return data

@njit(cache=True,inline='always')
def get(data,bit,width):
    if width==0:return np.uint64(0)
    word=bit>>6;shift=bit&63
    value=data[word]>>np.uint64(shift)
    if shift+width>64:value|=data[word+1]<<np.uint64(64-shift)
    return value & (np.uint64(0xFFFFFFFFFFFFFFFF)>>np.uint64(64-width))

@njit(cache=True,inline='always')
def put(data,bit,width,value):
    if width==0:return
    word=bit>>6;shift=bit&63
    mask=np.uint64(0xFFFFFFFFFFFFFFFF)>>np.uint64(64-width)
    value=np.uint64(value)&mask
    data[word]=(data[word]&~(mask<<np.uint64(shift)))|(value<<np.uint64(shift))
    if shift+width>64:
        high=shift+width-64
        highmask=np.uint64(0xFFFFFFFFFFFFFFFF)>>np.uint64(64-high)
        data[word+1]=(data[word+1]&~highmask)|(value>>np.uint64(64-shift))

@njit(cache=True,inline='always')
def lookup(data,h,q,r,sb,ways,code):
    if q==0:return False
    h=np.uint64(h)
    bucket=np.int64(h>>np.uint64(64-q))
    rem=(h>>np.uint64(64-q-r))&((np.uint64(1)<<np.uint64(r))-np.uint64(1))
    for way in range(ways):
        rec=256+(bucket*ways+way)*sb
        if get(data,rec+r+6,1)==0:continue
        length=np.int64(get(data,rec+r,6))
        stored=get(data,rec,r)
        if (stored>>np.uint64(r-length))==(rem>>np.uint64(r-length)):
            if code==0:put(data,rec+r+7,1,np.uint64(1))
            elif code==1:
                data[0]+=np.uint64(1);put(data,rec+r+7,64,data[0])
            return True
    return False

@njit(cache=True,inline='always')
def insert(data,h,length,q,r,sb,ways,code,handbits):
    if q==0 or length>q+r or length>=65:return 0
    bucket=np.int64(np.uint64(h)>>np.uint64(64-q));first=bucket*ways
    choice=-1
    for w in range(ways):
        if get(data,256+(first+w)*sb+r+6,1)==0:choice=w;break
    evicted=choice==-1
    if choice==-1:
        if code==1:
            oldest=np.uint64(0xFFFFFFFFFFFFFFFF)
            for w in range(ways):
                stamp=get(data,256+(first+w)*sb+r+7,64)
                if stamp<=oldest:oldest=stamp;choice=w
        else:
            hp=256+(1<<q)*ways*sb+bucket*handbits
            hand=np.int64(get(data,hp,handbits))
            if code==2:choice=hand
            else:
                for _ in range(ways*2):
                    rec=256+(first+hand)*sb
                    if get(data,rec+r+7,1)==0:choice=hand;break
                    put(data,rec+r+7,1,np.uint64(0));hand=(hand+1)%ways
            put(data,hp,handbits,np.uint64((choice+1)%ways))
    rec=256+(first+choice)*sb
    rem=(np.uint64(h)>>np.uint64(64-q-r))&((np.uint64(1)<<np.uint64(r))-np.uint64(1))
    put(data,rec,r,rem);put(data,rec+r,6,np.uint64(max(0,length-q)))
    put(data,rec+r+6,1,np.uint64(1))
    if code==1:
        data[0]+=np.uint64(1);put(data,rec+r+7,64,data[0])
    else:put(data,rec+r+7,1,np.uint64(1))
    return 2 if evicted else 1

@njit(cache=True)
def invalidate(data,h,q,r,sb,ways):
    if q==0:return 0
    bucket=np.int64(np.uint64(h)>>np.uint64(64-q))
    rem=(np.uint64(h)>>np.uint64(64-q-r))&((np.uint64(1)<<np.uint64(r))-np.uint64(1))
    removed=0
    for w in range(ways):
        rec=256+(bucket*ways+w)*sb
        if get(data,rec+r+6,1):
            length=np.int64(get(data,rec+r,6))
            if get(data,rec,r)>>np.uint64(r-length)==rem>>np.uint64(r-length):
                put(data,rec+r+6,1,np.uint64(0));removed+=1
    return removed

@njit(cache=True)
def replay(stream,hashes,safe,fp,data,q,r,sb,ways,code,hb,limit,placement,admit,
           probation,valid,fp_seen):
    # FP, hits, inserts, evictions, bypasses, processed, cutoff, occupied.
    counts=np.zeros(8,np.int64)
    for i in range(len(stream)):
        x=np.int64(stream[i]);raw=fp[x]
        if placement==1 and not raw:
            counts[5]+=1;continue
        h=hashes[x]
        if lookup(data,h,q,r,sb,ways,code):counts[1]+=1
        elif raw:
            counts[0]+=1
            if len(fp_seen):fp_seen[x]=True
            if counts[0]>limit:
                counts[5]=i+1;counts[6]=1;return counts
            allowed=True
            if admit==2 and len(probation):
                slot=np.int64(h%np.uint64(len(probation)))
                allowed=valid[slot] and probation[slot]==h
                probation[slot]=h;valid[slot]=True
            if allowed:
                outcome=insert(data,h,safe[x],q,r,sb,ways,code,hb)
                if outcome:
                    counts[2]+=1
                    if outcome==2:counts[3]+=1
                    else:counts[7]+=1
                else:counts[4]+=1
        counts[5]+=1
    return counts

def simulate(stream,hashes,safe,fp,cache_bytes,policy='clock',prefix_bits=40,ways=4,
             limit=2**62,placement='before',admit=1,collect=False):
    probation_entries=256 if admit==2 and cache_bytes>=256*9+2*ARRAY_HEADER+256 else 0
    probation_bytes=256*9+2*ARRAY_HEADER if probation_entries else 0
    spec=layout(max(0,cache_bytes-probation_bytes) if admit==1 or probation_entries else 0,prefix_bits,policy,ways)
    slab=allocate(spec)
    probation=np.zeros(probation_entries,np.uint64)
    valid=np.zeros(probation_entries,np.bool_)
    seen=np.zeros(len(hashes) if collect else 0,np.bool_)
    result=replay(np.asarray(stream,np.int64),hashes,safe,fp,slab,spec['qbits'],spec['rbits'],
                  spec['slot_bits'],ways,spec['policy_code'],spec['handbits'],int(limit),
                  1 if placement=='after' else 0,admit,probation,valid,seen)
    names=['fp','hits','inserts','evictions','bypasses','processed','cutoff','occupied']
    out={k:int(v) for k,v in zip(names,result)}
    out.update(spec)
    out['probation_bytes']=probation_bytes
    out['allocated_bytes']+=probation_bytes
    out['distinct_fp_keys']=int(seen.sum()) if collect else None
    return out
