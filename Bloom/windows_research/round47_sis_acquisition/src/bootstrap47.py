"""Install one verified prebuilt tool locally, without compiler/system installation."""
from pathlib import Path,PurePosixPath
import subprocess,json,hashlib,tarfile,time,os
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
BOTTLE_SHA='0d82a2ae7e022957f0f0675433d8e01622f3ce1a42c2cc7c76ce902f3685744c'
BOTTLE_URL='https://ghcr.io/v2/homebrew/core/zpaq/blobs/sha256:'+BOTTLE_SHA
TOKEN_URL='https://ghcr.io/token?service=ghcr.io&scope=repository:homebrew/core/zpaq:pull'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');tmp.replace(p)

def check():
    f=json.loads((ROOT/'plan/acquisition-freeze.json').read_text())
    for rel,h in f['sources'].items():assert sha(BLOOM/rel)==h,rel


def bootstrap():
    check();start=time.perf_counter();folder=ROOT/'tools/bottle';folder.mkdir(parents=True,exist_ok=False)
    token=json.loads(subprocess.check_output(['curl','--silent','--show-error','--fail','--proto','=https','--max-time','30',TOKEN_URL]))['token']
    archive=folder/'zpaq.tar.gz'
    # Anonymous public registry token is never printed or stored in result/log files.
    with (folder/'curl.log').open('x') as f:
        subprocess.run(['curl','--fail','--location','--proto','=https','--proto-redir','=https','--max-time','60','--max-filesize',str(10*1024**2),'--header','Authorization: Bearer '+token,'--output',str(archive),BOTTLE_URL],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=70)
    del token
    assert sha(archive)==BOTTLE_SHA,'Prebuilt artifact hash mismatch'
    output=ROOT/'tools/executable';output.mkdir(parents=True,exist_ok=False);binary=output/'zpaq'
    with tarfile.open(archive,'r:gz') as tf:
        candidates=[m for m in tf.getmembers() if m.name.endswith('/bin/zpaq')]
        assert len(candidates)==1;m=candidates[0]
        assert m.isfile() and not m.issym() and not m.islnk() and m.size<10*1024**2 and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts
        stream=tf.extractfile(m)
        with binary.open('xb') as f:f.write(stream.read())
    os.chmod(binary,0o755)
    kind=subprocess.check_output(['/usr/bin/file',str(binary)],text=True);deps=subprocess.check_output(['/usr/bin/otool','-L',str(binary)],text=True)
    assert 'Mach-O' in kind and 'arm64' in kind
    for line in deps.splitlines()[1:]:assert line.strip().startswith(('/usr/lib/','/System/Library/')), 'Non-system runtime dependency'
    help_result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=15,cwd=BLOOM)
    help_text=help_result.stdout+help_result.stderr;assert 'zpaq' in help_text.lower() and '7.15' in help_text
    (ROOT/'results/tool_help.txt').write_text(help_text)
    save(ROOT/'results/tool.json',dict(status='verified',bottle_sha256=BOTTLE_SHA,binary_sha256=sha(binary),bottle_bytes=archive.stat().st_size,binary_bytes=binary.stat().st_size,version='zpaq7.15revision1',platform='arm64_sequoia official Homebrew bottle',local_compilation=False,global_install=False,seconds=time.perf_counter()-start,architecture=kind.strip(),dependencies=deps.splitlines()[1:]))
    check();print('LOCAL_PREBUILT_TOOL_VERIFIED',flush=True)

if __name__=='__main__':
    try:bootstrap()
    except BaseException as e:save(ROOT/'results/tool_failure.json',dict(status='failed',error=repr(e)));raise
