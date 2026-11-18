"""Experiment matrix for the post-hoc zero-tree method extension."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
TCP={'caida_tcp_flow':(16,32,63,189),'mawi2020_tcp_flow':(32,64,127,381),
     'mawi2021_tcp_flow':(21,41,81,242),'mawi2022_tcp_flow':(32,64,128,382)}
MID={'cod':1024,'url':128,'caida':256,'shalla':1024}
FRESH={'caida':(128,256,1024,2048),'shalla':(256,1024,2048,4096)}
DATASETS=tuple(TCP)+tuple(MID)
METHODS=('RA6-Z','RA6','Zero-Predict','Gama','BF','BF+ReplayCache','Replay','Replay+Z')


def cases(ds):
    if ds in TCP:return [(k,'真实轨迹',0,'weak_tcp') for k in TCP[ds]]
    out=[(MID[ds],w,s,'model_control') for w in ('zipf1.0-全部','每key一次') for s in range(5)]
    out += [(k,'全新对抗',s,'fresh_adversarial') for k in FRESH.get(ds,()) for s in range(5)]
    return out


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def ah(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()


def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
