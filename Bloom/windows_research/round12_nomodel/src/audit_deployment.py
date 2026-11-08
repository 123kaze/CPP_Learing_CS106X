"""Fixed-input collision / deployment-state audit and a feature-overlap reporting erratum.

This is not an independent holdout and does not establish adversarial probability bounds.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import baseline as B

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):
            h.update(chunk)
    return h.hexdigest()


def exact_pairs(x, y):
    assert x.ndim == 2 and x.shape[1] == 2 and np.isfinite(x).all()
    x=np.ascontiguousarray(x)
    pairs=x.view(np.dtype([('src',x.dtype),('dst',x.dtype)])).reshape(-1)
    return int(np.isin(pairs[~y],pairs[y]).sum())


def main():
    out=ROOT/'results'
    out.mkdir(parents=True,exist_ok=True)
    old_meta=json.loads((B.WR/'round11_tcp/results/datasets.json').read_text())
    rows=[]
    for ds in ('cod','url','shalla',*old_meta):
        s,safe,paths=B.load_setup(ds,'fp64')
        assert safe is None and not hasattr(s,'member_hashes')
        # Audit workspace only: not needed by deployed lookup or insertion.
        collisions=np.intersect1d(s.h1m,s.h1q)
        r=dict(dataset=ds,members=len(s.h1m),test_negatives=len(s.h1q),
               common_member_negative_fingerprints=int(len(collisions)),
               fp64_loader_has_sorted_member_index=False,
               input_sha256={str(p.relative_to(B.WR.parent)):sha(p) for p in paths})
        if ds in old_meta:
            p=B.C.CACHE/ds/'data.npz'
            with np.load(p,allow_pickle=False) as d:
                x,y=d['X'],d['y']
            actual=exact_pairs(x,y)
            old=old_meta[ds]['negatives_sharing_model_input_with_member']
            lossy=x[:,0].astype(np.float64)*2**33+x[:,1].astype(np.float64)
            recomputed_old=int(np.isin(lossy[~y],lossy[y]).sum())
            assert recomputed_old==old
            r.update(all_negative_flows=int((~y).sum()),reported_shared_model_inputs=old,
                     corrected_shared_model_inputs=actual,corrected_fraction=actual/int((~y).sum()))
        rows.append(r)
        print(ds,'fingerprint collisions',len(collisions),flush=True)
    # Deterministic injected same-fingerprint example: fp64 is NOT one-sided error.
    F=B.cache_fp
    spec=F.layout(1024)
    data=F.allocate(spec)
    h=np.uint64(123456)
    args=(spec['buckets'],spec['prefix_bits'],spec['Q'],spec['ob'],spec['slot_bits'],spec['ways'])
    assert F.insert(data,h,*args,spec['handbits'])==1
    assert F.lookup(data,h,*args)
    proof=dict(injected_identical_fingerprint_causes_cache_hit=True,
               note='A distinct member sharing a cached negative fingerprint would be rejected.')
    (out/'deployment_audit.json').write_text(json.dumps(dict(datasets=rows,collision_test=proof),indent=2)+'\n')
    lines=['# 指纹缓存部署边界与旧特征统计勘误', '', '## 部署内存', '',
           '- 本轮纯 BF 查询只需要一个 owning uint64 数组；32 B 元数据和位图都在数组里，数组头也计入预算。缓存另按自身 owning 数组计费。',
           '- fp64 的缓存查找/插入只接收缓存数组、查询指纹和布局参数，不需要成员索引。构建输入、模型/流生成缓存、验证工作区与部署状态不同。',
           '- 本轮 fp64 数据加载不计算 safe 长度、不创建排序成员索引。旧 round10 的 E5.load 仍会计算 safe，不能把其整个实验进程称作“没有预算外内存”。',
           '- 宿主解释器、Numba/JIT、查询输入、后端真值和选择期工作区仍不计入 AMQ 结构预算；这里没有声称进程 RSS 等于预算。', '',
           '## 固定数据上的完整指纹碰撞检查', '',
           '| 数据 | 成员 | 测试负例 | 两者共享的 64 位指纹 |',
           '|---|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['dataset']} | {r['members']:,} | {r['test_negatives']:,} | {r['common_member_negative_fingerprints']} |")
    lines += ['', '所有检查为 0 时，可说明这些固定成员与固定测试负例之间不存在指纹碰撞：在仅插入该测试池负例、且完整指纹匹配正确实现的前提下，缓存不会因为这类碰撞拒绝成员。',
              '这比只看最终快照强，但不覆盖未检查的未来 key、动态成员集合、非指纹实现缺陷或对抗查询。',
              '强制给两个不同角色使用同一指纹的测试确实会产生缓存命中，因此 fp64 并不具备严格零假阴性的结构性保证。', '',
              '在独立、均匀 64 位指纹的理想模型下，固定 S 个缓存指纹与一个独立成员指纹碰撞的概率可用 S/2^64 联合界估计；Q 次查询还需按相应假设考虑 Q 倍联合界。',
              '不能将最后快照占用量代入后称为整个运行过程或任意自适应查询的保证。现有固定 pandas 哈希和 SplitMix64 实现不构成这里所假设的随机独立哈希证明。', '',
              '## TCP-only 模型输入重合比例的勘误', '',
              '旧 `tcp11.py` 用 `src*2**33 + dst` 的 float64 值代替二维特征对；数值较大时低位精度不足，不同 dst 被合并。',
              '下面直接以两个 float32 字段组成的结构化数组比较，保留模型实际接收的两个值；旧算法的输出也重新计算并与存档核对一致。', '',
              '| 数据 | 原记录重合数 | 二维精确比较重合数 | 负例流数 | 修正比例 |',
              '|---|---:|---:|---:|---:|']
    for r in rows:
        if 'corrected_fraction' in r:
            lines.append(f"| {r['dataset']} | {r['reported_shared_model_inputs']:,} | {r['corrected_shared_model_inputs']:,} | "
                         f"{r['all_negative_flows']:,} | {r['corrected_fraction']:.2%} |")
    lines += ['', '旧的 40%–83% 应改为约 30%–74%。这处算式只用于生成统计字段，不用于成员定义、训练输入或查询，所以不改变旧误报计数。',
              '两个特征相同的负例占比，以及选出少量树，都不能单独证明“模型完全无用”；模型价值应依据同预算 BF+缓存等对照来讨论。',
              'IPv4 转 float32 的舍入也不是固定 /24 截断；精度随数值范围变化。旧说明里的“约 /24”不应理解为实际预处理规则。', '',
              '旧冻结脚本和原始数据统计保留。本文件为可复现勘误，非新方法或新留出实验。']
    (out/'deployment_audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
