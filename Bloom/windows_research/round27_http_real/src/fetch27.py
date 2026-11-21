"""Bounded range resume of two fixed public datasets. No archive code is executed."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data27 import save,sha
import gzip
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1]
FILES=[dict(name='nasa_jul95',filename='NASA_access_log_Jul95.gz',url='https://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz',size=20676672,partial='inputs/nasa_jul95/NASA_access_log_Jul95.gz'),
       dict(name='nasa_aug95',filename='NASA_access_log_Aug95.gz',url='https://raw.githubusercontent.com/COM6012/ScalableML/master/Data/NASA_access_log_Aug95.gz',size=16633316,partial='inputs/nasa_aug95_github/NASA_access_log_Aug95.gz')]


def fetch_part(spec,i,lo,hi,folder):
    # Each downloaded part in its own new empty directory; scripts are elsewhere.
    directory=folder/f'part{i}';directory.mkdir();dest=directory/'payload.part';header=directory/'headers.txt'
    r=subprocess.run(['curl','--fail','--silent','--show-error','--location','--connect-timeout','20','--max-time','1800',
                      '--range',f'{lo}-{hi}','--dump-header',str(header),'--output',str(dest),spec['url']],capture_output=True,text=True,cwd=ROOT.parents[1])
    record=dict(part=i,start=lo,end=hi,exit_code=r.returncode,stderr=r.stderr,received=dest.stat().st_size if dest.exists() else 0)
    save(directory/'receipt.json',record)
    assert r.returncode==0,(spec['name'],record)
    assert dest.stat().st_size==hi-lo+1,(dest,'Wrong range byte count')
    assert f'content-range: bytes {lo}-{hi}/{spec["size"]}' in header.read_text().lower(),(header,'Server did not honor range')
    record['sha256']=sha(dest);save(directory/'receipt.json',record)
    print('PART COMPLETE',spec['name'],i,hi-lo+1,flush=True)
    return dest,record


def main():
    futures={};receipts={};parts={};folders={}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for spec in FILES:
            folder=ROOT/'inputs'/f'{spec["name"]}_range_resume';folder.mkdir();folders[spec['name']]=folder
            prefix=ROOT/spec['partial'];offset=prefix.stat().st_size;assert 0<offset<spec['size']
            receipts[spec['name']]=dict(**spec,partial_bytes=offset,partial_sha256=sha(prefix),parts=[])
            size=(spec['size']-offset+3)//4
            for i,lo in enumerate(range(offset,spec['size'],size)):
                hi=min(spec['size']-1,lo+size-1);f=pool.submit(fetch_part,spec,i,lo,hi,folder);futures[f]=(spec['name'],i)
        for f in as_completed(futures):
            name,i=futures[f];dest,rec=f.result();parts[name,i]=dest;receipts[name]['parts'].append(rec)
    for spec in FILES:
        folder=folders[spec['name']];outdir=folder/'assembled';outdir.mkdir();output=outdir/spec['filename']
        receipt=receipts[spec['name']];assert sha(ROOT/spec['partial'])==receipt['partial_sha256']
        with output.open('xb') as dst:
            for source in [ROOT/spec['partial'],*[parts[spec['name'],i] for i in range(len(receipt['parts']))]]:
                with source.open('rb') as src:
                    for block in iter(lambda:src.read(1<<20),b''):dst.write(block)
        assert output.stat().st_size==spec['size']
        decompressed=hashlib.sha256();uncompressed_size=0
        with gzip.open(output,'rb') as f:
            for block in iter(lambda:f.read(1<<20),b''):decompressed.update(block);uncompressed_size+=len(block)
        receipt.update(status='complete_crc_verified',sha256=sha(output),uncompressed_sha256=decompressed.hexdigest(),uncompressed_bytes=uncompressed_size,assembled_path=str(output.relative_to(ROOT)),source_note='Partial download preserved; byte ranges resumed from SAME URL; archive filename fixed before download.')
        receipt['parts'].sort(key=lambda r:r['part']);save(ROOT/f'results/data_{spec["name"]}_download.json',receipt)
        print('DOWNLOAD COMPLETE',spec['name'],receipt['sha256'],flush=True)


if __name__=='__main__':main()
