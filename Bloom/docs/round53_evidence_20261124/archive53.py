"""Check existing per-version archives and create a new outer manifest; never rewrite old manifests."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;BLOOM=HERE.parents[1]
ROUNDS=[BLOOM/'windows_research'/('round53_index_free_recheck'+s) for s in ('','_v2','_v3','_v4')]


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def main():
    dest=HERE/'archive_manifest.json';assert not dest.exists()
    checked=0;files=[]
    for root in ROUNDS:
        archive=json.loads((root/'archive_manifest.json').read_text())
        for item in archive['files']:
            p=root/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],str(p)
            checked+=1
        for p in sorted(root.rglob('*')):
            if not p.is_file() or any(k in p.parts for k in ('cache','__pycache__')):continue
            if p.suffix not in ('.py','.md','.json','.csv','.log') and p.name!='.gitignore':continue
            files.append(p)
    files += [p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.json','.md') and p!=dest]
    files.append(BLOOM/'docs/第53轮无索引重跑执行记录_20261124.md')
    records=[dict(path=str(p.relative_to(BLOOM)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(set(files))]
    dest.write_text(json.dumps(dict(status='verified',existing_archive_entries_checked=checked,files=records,note='Outer manifest includes subsequent status READMEs; historical per-version manifests remain byte-identical. Raw inputs/cache/JIT binaries excluded; not a publication receipt.'),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(existing_archive_entries_checked=checked,outer_files=len(records),bytes=sum(r['bytes'] for r in records))))


if __name__=='__main__':main()
