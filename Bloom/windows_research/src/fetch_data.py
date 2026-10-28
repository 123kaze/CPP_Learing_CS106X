"""Fetch primary-source datasets; never touch old research trees."""
from pathlib import Path
import requests, tarfile, json, hashlib, time
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
DATA.mkdir(exist_ok=True)
def caida():
    url='https://raw.githubusercontent.com/saltsystemslab/How-to-Train-Your-Filter/c970c34/data/compressed/caida.tar.gz'
    dest=DATA/'caida.tar.gz'
    if not dest.exists() or dest.stat().st_size != 90373526:
        with requests.get(url,stream=True,timeout=(30,120)) as r:
            r.raise_for_status()
            with dest.open('wb') as out:
                for chunk in r.iter_content(1<<20):
                    out.write(chunk)
                    print(out.tell(),flush=True)
    assert dest.stat().st_size==90373526
    with tarfile.open(dest) as tar:
        members=[m for m in tar.getmembers() if m.name.endswith('caida.csv') and m.isfile()]
        assert len(members)==1
        with tar.extractfile(members[0]) as src, (DATA/'caida.csv').open('wb') as dst:
            import shutil
            shutil.copyfileobj(src,dst)
    meta=dict(url=url,archive_bytes=dest.stat().st_size,sha256=hashlib.file_digest(dest.open('rb'),'sha256').hexdigest())
    (DATA/'caida-source.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(meta,flush=True)
if __name__=='__main__': caida()
