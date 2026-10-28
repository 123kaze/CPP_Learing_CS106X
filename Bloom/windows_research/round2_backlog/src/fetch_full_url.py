from pathlib import Path
import requests,zipfile,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
url='https://www.kaggle.com/api/v1/datasets/download/sid321axn/malicious-urls-dataset'
dest=ROOT/'data'/'url-full.zip'
with requests.get(url,stream=True,timeout=(30,120)) as r:
    r.raise_for_status()
    with dest.open('wb') as out:
        for chunk in r.iter_content(1<<20):out.write(chunk)
with zipfile.ZipFile(dest) as z:
    names=[s for s in z.namelist() if s.endswith('.csv')]
    assert len(names)==1
    source=ROOT/'data'/'malicious_phish_full.csv'
    with z.open(names[0]) as inp,source.open('wb') as out:shutil.copyfileobj(inp,out)
old=ROOT/'cache'/'url';archived=ROOT/'cache'/'url_httyf_subset'
assert old.resolve().is_relative_to(ROOT.resolve()) and archived.resolve().is_relative_to(ROOT.resolve())
if old.exists() and not archived.exists():old.rename(archived)
(ROOT/'data'/'url-full-source.json').write_text(json.dumps(dict(url=url,archive_bytes=dest.stat().st_size,archive_sha256=hashlib.file_digest(dest.open('rb'),'sha256').hexdigest(),file=source.name),indent=2),encoding='utf-8')
print('FULL URL SOURCE READY',source,source.stat().st_size,flush=True)
