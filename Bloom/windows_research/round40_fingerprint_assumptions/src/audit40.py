"""Exact shared-hash admission-bias audit; no sampled 64-bit collision is claimed."""
from pathlib import Path
from fractions import Fraction
from itertools import product
from math import comb,prod
import hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]


def occupancy(m,n):
    if min(m,n)<1:raise ValueError('Nonempty BF and members required')
    s=[[0]*(n+1) for _ in range(n+1)];s[0][0]=1
    for i in range(1,n+1):
        for k in range(1,i+1):s[i][k]=s[i-1][k-1]+k*s[i-1][k]
    result={k:Fraction(prod(range(m-k+1,m+1))*s[n][k],m**n) for k in range(1,min(m,n)+1)}
    assert sum(result.values(),Fraction(0))==1
    return result


def lower_bound(bits,m,n,slots,queries):
    U=2**bits
    if U%m or slots<1 or queries<1:raise ValueError('Divisible universe and positive sizes required')
    a=Fraction(1,U);answer=Fraction(0)
    for occupied,mass in occupancy(m,n).items():
        p=Fraction(occupied,m)
        # At least one fixed-member alias AND at most slots BF-admitted queries: no eviction.
        conditional=sum((comb(queries,j)*(1-p)**(queries-j)*(p**j-(p-a)**j)
                         for j in range(1,min(slots,queries)+1)),Fraction(0))
        answer+=mass*conditional
    return answer


def enumerate_small():
    """Four distinct raw keys: two members, then two negatives; independently 2-bit hashed."""
    U=4;m=4;slots=1;total=hits=sufficient=0
    for member in product(range(U),repeat=2):
        bf={h%m for h in member}
        for negative in product(range(U),repeat=2):
            cache=None;accepted=0
            for h in negative:
                if h%m in bf:accepted+=1
                if cache==h:continue
                if h%m in bf:cache=h  # Exact raw-key backend says absent for these negative keys.
            hits+=cache==member[0]
            sufficient+=member[0] in negative and accepted<=slots
            total+=1
    return dict(assignments=total,actual=Fraction(hits,total),sufficient=Fraction(sufficient,total),naive=Fraction(slots,U))


def fraction_record(x):return dict(numerator=str(x.numerator),denominator=str(x.denominator),decimal=float(x))


def native_contract():
    sys.path.insert(0,str(BLOOM/'windows_research/round12_nomodel/src'))
    import baseline as B
    C=B.C;F=B.CACHES['fp64'];K=B.CACHES['index'];np=B.np
    pure_budget=B.ARRAY_HEADER+B.HEAD_WORDS*8+8
    data=B.allocate(64,pure_budget,0)
    assert (int(data[1]),int(data[2]))==(64,1)
    hashes=np.arange(64,dtype=np.uint64);B.insert_all(data,hashes);assert B.query_all(data,hashes).all()
    cb=F._bytes(1,64,4)[0];sp=F.layout(cb)
    assert sp['buckets']==1 and sp['slots']==4 and sp['prefix_bits']==64
    fp=F.allocate(sp);F.insert(fp,np.uint64(0),sp['buckets'],64,sp['Q'],sp['ob'],sp['slot_bits'],4,sp['handbits'])
    assert F.lookup(fp,np.uint64(0),sp['buckets'],64,sp['Q'],sp['ob'],sp['slot_bits'],4)
    ip=K.layout(cb);safe=B.E5.E.CC.safe_prefix_lengths(np.array([0],np.uint64),np.array([0],np.uint64));assert int(safe[0])==65
    index=K.allocate(ip);K.insert(index,np.uint64(0),int(safe[0]),ip['buckets'],40,ip['Q'],ip['ob'],ip['slot_bits'],4,ip['handbits'])
    assert K.count_member_hits(index,np.array([0],np.uint64),ip['buckets'],40,ip['Q'],ip['ob'],ip['slot_bits'],4)==0
    return dict(BF_member_count=64,BF_bits=64,BF_probes=1,BF_total_bytes=pure_budget,
                fp64_cache_bytes=cb,fp64_slots=4,fp64_representation_alias_hits=True,index_alias_safe_length=65,index_member_hits=0,
                note='Native parameter and injected-representation checks, not a discovered hash collision or measured collision frequency')


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    start=time.perf_counter();freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in freeze['sources'].items():assert sha(BLOOM/p)==h,p
    output=ROOT/'results/verification.json';assert not output.exists(),'Refuse overwrite'
    small=enumerate_small();assert small['assignments']==256
    assert small['sufficient']==lower_bound(2,4,2,1,2)
    assert small['actual']>=small['sufficient']>small['naive']
    start_native=time.perf_counter();native=native_contract();native_s=time.perf_counter()-start_native
    results=[];t=time.perf_counter()
    for bits in (8,16,64):
        lower=lower_bound(bits,64,64,4,5);naive=Fraction(4,2**bits);assert lower>naive
        results.append(dict(bits=bits,m=64,members=64,slots=4,negative_queries=5,lower_bound=fraction_record(lower),
                            capacity_over_universe=fraction_record(naive),lower_over_naive=fraction_record(lower/naive)))
    probability_s=time.perf_counter()-t
    result=dict(status='verified',audit_kind='posthoc exact-probability assumption audit',
        small_enumeration={k:(fraction_record(v) if isinstance(v,Fraction) else v) for k,v in small.items()},
        native=native,probability_cases=results,native_check_s=native_s,exact_probability_s=probability_s,
        wall_s=time.perf_counter()-start,freeze_sha256=sha(ROOT/'plan/freeze.json'),
        changes_old_FP_or_FN_observations=False,independent_hash_variant_implemented=False)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    text=['# Round40：指纹概率保证的独立性前提','',
          '**结论：仅“理想均匀、非恶意哈希输入”不足以直接推出共享hash负缓存的S/2^64界。** BF只让一部分hash值通过，缓存再从其中收集负key，目标member的hash与这个入选事件相关。', '',
          '这是事后数学/正确性审计，不是新工作负载实验，不修改旧FP/FN结果，也没有发现实际64-bit碰撞。', '',
          '## 无需选择特定member哈希的反例', '',
          '64个预先固定member keys，5个预先固定nonmember keys，原始key身份互异；理想随机哈希给出独立均匀fingerprints。64-bit BF、1个probe及单桶4-slot cache都是有效原语配置，冻结baseline对n=64,m=64确实选择k=1。BF的probe来自同一fingerprint的双射变换mod64。', '',
          '设BF占用K格，p=K/64，a=1/2^b。事件“至少一次命中指定member的fingerprint，且5个负查询中至多4个能过BF”确保别名入cache且无容量淘汰，因此给出FN概率下界：', '',
          '`1-(1-a)^5 - [p^5-(p-a)^5]`。', '',
          '将这个表达式按完整member哈希分布取期望（用精确occupancy/Stirling分布），而不是条件挑选member哈希，得到：', '',
          '| fingerprint bits | FN概率下界 | S/2^b（S=4） | 下界/该数 |',
          '| --- | ---: | ---: | ---: |']
    for r in results:text.append(f'| {r["bits"]} | {r["lower_bound"]["decimal"]:.12g} | {r["capacity_over_universe"]["decimal"]:.12g} | {r["lower_over_naive"]["decimal"]:.9f} |')
    text += ['', '64-bit结果是精确概率计算，不是Monte Carlo。源码中每个有理数的分子/分母都按字符串保存，避免JSON浮点损失。小模型另穷举全部256种哈希赋值，验证无淘汰事件计算；原始member/query身份不同，backend依原始身份确认negative。', '',
             '## 应如何更正保证', '',
             '- 当前有限数据集的无碰撞/0FN检查仍有效；本审计不把理论反例当成已发生线上错误。',
             '- S/2^64需要目标指纹与给定cache内容/入选过程适当独立的条件。当前共享hash实现不能仅凭非恶意输入就自动使用该条件；旧报告中的这一数值应视作依赖额外假设的参考量，而不是已证明的通用上界。',
             '- 对哈希前固定的n个members和Q个不同negative原始keys，在理想均匀指纹模型下可用某固定member的min(1,Q/2^64)或全部members的min(1,nQ/2^64)作为保守有限集合碰撞界。它们与cache驻留多少无关，也不是无限期或敌对键保证。',
             '- 要恢复容量型界，应建立独立cache fingerprint与入选过程的条件独立性。应从原始key或无碰撞身份构造独立哈希；给同一个已压缩64-bit值再次加盐不能恢复信息或消除共享碰撞。这个新变体尚未实现/计时，不追认其性质给旧实现。',
             '- 若精确key域本身就是uint64且使用双射编码，完整64-bit cache是精确key缓存特例；任意字符串压缩为64 bits不属于此特例。',
             '- strict zero-FN要求下，继续使用带完整静态索引并安全验证的prefix方案，或无负cache的BF，或另行计费的精确key cache。不能把很小的概率当作不可能。', '',
             '## 原代码与结果边界', '',
             '- 原cache_fp.py:12-16中的概率说明未改；本目录作为可追溯勘误。BF probes使用h1，fp64 cache也消费h1，这正是需要审查的共享依赖。',
             '- 原生注入相同表示时，fp64命中该member表示；verified-prefix得到safe length=65并bypass。它重现的是表示别名的语义，不是寻找到真实哈希碰撞。',
             '- 第29/38轮原来保存的S/2^64参考值不被静默重写；应与本勘误一起阅读。第38/39轮的实际FP、预算和有限成员检查不因此改变。',
             '- 本审计不修改论文，也不提供完整selector的最优/收敛保证。']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n')
    print('VERIFIED_FP_ASSUMPTIONS',json.dumps(dict(bits64_lower=results[-1]['lower_bound']['decimal'],bits64_naive=results[-1]['capacity_over_universe']['decimal'],ratio=results[-1]['lower_over_naive']['decimal'],small_assignments=small['assignments'])),flush=True)


if __name__=='__main__':main()
