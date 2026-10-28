"""Acquire original benchmark inputs, preserving old cache files read-only."""
from pathlib import Path
import requests,tarfile,shutil,json,hashlib,subprocess,os,sys
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent
def download(ds,expected):
    url=f'https://raw.githubusercontent.com/saltsystemslab/How-to-Train-Your-Filter/c970c34/data/compressed/{ds}.tar.gz'
    dest=ROOT/'data'/f'{ds}.tar.gz'
    if not dest.exists() or dest.stat().st_size!=expected:
        with requests.get(url,stream=True,timeout=(30,120)) as response:
            response.raise_for_status()
            with dest.open('wb') as out:
                for chunk in response.iter_content(1<<20):out.write(chunk)
        assert dest.stat().st_size==expected
    names=[]
    with tarfile.open(dest) as archive:
        for member in archive.getmembers():
            if member.isfile() and member.name.endswith('.csv'):
                name=Path(member.name).name
                with archive.extractfile(member) as src,(ROOT/'data'/name).open('wb') as out:shutil.copyfileobj(src,out)
                names.append(name)
    meta=dict(url=url,sha256=hashlib.file_digest(dest.open('rb'),'sha256').hexdigest(),archive_bytes=expected,files=names)
    (ROOT/'data'/f'{ds}-source.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(ds,meta,flush=True)
def link_existing():
    for ds in ('cod','caida'):
        folder=ROOT/'cache'/ds;folder.mkdir(exist_ok=True)
        for source in (OLD/'cache'/ds).iterdir():
            if source.name in ('data.npz','gama_scores.npz','scores.npz','model200.txt','model48.txt'):
                dest=folder/source.name
                if not dest.exists():os.link(source,dest)
    print('linked read-only existing COD/Caida data and models',flush=True)
def sources():
    folder=ROOT/'external'/'httyf'
    if not (folder/'.git').exists():
        info=requests.get('https://api.github.com/repos/saltsystemslab/How-to-Train-Your-Filter/commits/c970c34',timeout=30);info.raise_for_status()
        sha=info.json()['sha']
        subprocess.run(['git','init',str(folder)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(folder),'remote','add','origin','https://github.com/saltsystemslab/How-to-Train-Your-Filter.git'],check=True)
        subprocess.run(['git','-C',str(folder),'config','core.longpaths','true'],check=True)
        subprocess.run(['git','-C',str(folder),'sparse-checkout','init','--cone'],check=True)
        subprocess.run(['git','-C',str(folder),'sparse-checkout','set','adaptiveqf'],check=True)
        subprocess.run(['git','-C',str(folder),'fetch','--depth=1','--filter=blob:none','origin',sha],check=True)
        subprocess.run(['git','-C',str(folder),'checkout','--detach','FETCH_HEAD'],check=True)
    print('upstream source ready',flush=True)
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    link_existing()
    download('shalla',53971021)
    download('url',6113969)
    sources()
