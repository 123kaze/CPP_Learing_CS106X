"""Bounded serial download of three preselected public CC-BY4.0 request samples."""
from pathlib import Path
import json,hashlib,subprocess,time,shutil
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
COMMIT='1c503676d6972d4394a360e09162149a6c00f516'
FILES=(('cluster001',81189662,'fc5d8a10f9aed97e2f75b0b57db66e734d2bbbdb'),('cluster002',44555350,'b6119bbbc6b07301d8e11f01aadae0e78e1f4f99'),('cluster003',40207548,'52abd1be4459656945bc1e3c5052570d7f75c9aa'))


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(path)

def main():
    started=time.perf_counter();freeze=json.loads((ROOT/'plan/download-freeze.json').read_text())
    for rel,h in freeze['sources'].items():assert sha(BLOOM/rel)==h,rel
    assert shutil.disk_usage(ROOT).free>=2*1024**3
    out=ROOT/'results/downloads.json';assert not out.exists();rows=[]
    for name,size,blob in FILES:
        folder=ROOT/'inputs'/name;folder.mkdir(parents=True,exist_ok=False)
        target=folder/'trace.csv';url=f'https://raw.githubusercontent.com/twitter/cache-trace/{COMMIT}/samples/2020Mar/{name}'
        t=time.perf_counter()
        with (folder/'curl.log').open('x') as log:
            result=subprocess.run(['curl','--fail','--location','--proto','=https','--proto-redir','=https','--connect-timeout','30','--max-time','300','--max-filesize',str(128*1024**2),'--dump-header',str(folder/'headers.txt'),'--output',str(target),url],stdout=log,stderr=subprocess.STDOUT,timeout=320)
        row=dict(name=name,url=url,expected_bytes=size,expected_git_blob_sha1=blob,seconds=time.perf_counter()-t,exit_code=result.returncode,status='downloaded_unverified')
        rows.append(row);save(out,dict(status='running',files=rows))
        assert result.returncode==0,'Download failed; retain partial bytes; do not retry'
        assert target.stat().st_size==size
        h=hashlib.sha1(f'blob {size}\0'.encode())
        with target.open('rb') as f:
            for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
        assert h.hexdigest()==blob,'Git blob identity mismatch'
        row.update(status='verified',bytes=size,sha256=sha(target),actual_git_blob_sha1=h.hexdigest());save(out,dict(status='running',files=rows))
        print('DOWNLOAD_VERIFIED',name,size,round(row['seconds'],3),flush=True)
    for rel,h in freeze['sources'].items():assert sha(BLOOM/rel)==h,rel
    save(out,dict(status='complete',files=rows,total_bytes=sum(x[1] for x in FILES),wall_s=time.perf_counter()-started,license='CC-BY-4.0',source_commit=COMMIT));print('DOWNLOAD_COMPLETE',flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as e:save(ROOT/'results/download_failure.json',dict(status='failed',error=repr(e)));raise
