import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];OLD=ROOT.parent/'round46_dns_qualification'
sys.path.insert(0,str(OLD/'src'))
import audit46 as A
import json,gzip,hashlib,time


def fields():
    names=[f'unused_{i}'.encode() for i in range(23)]
    for i,n in ((0,b'ts'),(8,b'query'),(11,b'qtype'),(12,b'qtype_name'),(13,b'rcode'),(14,b'rcode_name'),(20,b'answers')):names[i]=n
    return names


def validate(line):
    row=line.rstrip(b'\r\n').split(b'\t')
    if len(row)!=23:raise ValueError('Expected23fields')
    if row[11]==b'1' and row[12]!=b'A':raise ValueError('A type code/name mismatch')
    if row[13]==b'0' and row[14]!=b'NOERROR':raise ValueError('NOERROR code/name mismatch')
    if row[13]==b'3' and row[14]!=b'NXDOMAIN':raise ValueError('NXDOMAIN code/name mismatch')
    float(row[0]);return row


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for section in ('sources','inputs'):
        for p,h in f[section].items():assert A.sha(BLOOM/p)==h,p


def main():
    check();start=time.perf_counter();assert not (ROOT/'results/completion.json').exists()
    receipt=json.loads((OLD/'results/download.json').read_text());assert receipt['status']=='verified'
    source=OLD/'inputs/source/dns.log.gz';assert A.sha(source)==receipt['sha256']
    folder=ROOT/'cache';folder.mkdir(exist_ok=False);derived=folder/'with_declared_fields.gz';h=hashlib.sha256();size=count=0;t=time.perf_counter()
    with gzip.open(source,'rb') as src,gzip.open(derived,'wb') as dst:
        dst.write(b'#fields\t'+b'\t'.join(fields())+b'\n')
        while True:
            line=src.readline(65537)
            if not line:break
            assert len(line)<=65536;validate(line);h.update(line);size+=len(line);count+=1;dst.write(line)
    assert h.hexdigest()==receipt['uncompressed_sha256'] and size==receipt['uncompressed_bytes']
    A.save(ROOT/'results/schema_verification.json',dict(status='verified',original_body_sha256=h.hexdigest(),original_body_bytes=size,records=count,original_order_and_bytes_preserved=True,derived_sha256=A.sha(derived),mapping={n.decode():i for i,n in enumerate(fields()) if not n.startswith(b'unused')},source_schema_notebook_blob='1b5753b07d813b172d463dc656bca6e3feea1882',adapter_s=time.perf_counter()-t))
    previous=A.ROOT;A.ROOT=ROOT
    try:
        path,meta=A.parse(derived);eligible=A.diagnose(path,meta)
    finally:A.ROOT=previous
    check();A.save(ROOT/'results/completion.json',dict(status='complete',eligible_for_methods=eligible,wall_s=time.perf_counter()-start,old_failure_retained=True,old_code_modified=False));print('DNS_V2_COMPLETE',eligible,flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as e:A.save(ROOT/'results/failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:300]));raise
