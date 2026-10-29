"""A real file-backed KV get point, including Python/API/feedback overhead."""
from pathlib import Path
import sqlite3,time,json
import numpy as np
import engine as E
import live_pipeline as L

def run():
    setup,scores,safe=E.load('cod');_,_,X,_=E.C.load_dataset('cod')
    tmp=E.ROOT/'tmp';tmp.mkdir(exist_ok=True)
    database=tmp/'cod-members.sqlite'
    connection=sqlite3.connect(database)
    connection.execute('PRAGMA journal_mode=DELETE');connection.execute('PRAGMA synchronous=NORMAL')
    connection.execute('CREATE TABLE IF NOT EXISTS kv (key BLOB PRIMARY KEY,value BLOB NOT NULL) WITHOUT ROWID')
    count=connection.execute('SELECT COUNT(*) FROM kv').fetchone()[0]
    if count!=int(setup.y.sum()):
        assert count==0,'Unexpected existing database contents'
        keys=setup.ids[setup.y]
        connection.executemany('INSERT INTO kv VALUES (?,?)',((int(k).to_bytes(8,'big'),bytes(32)) for k in keys))
        connection.commit()
    assert connection.execute('SELECT COUNT(*) FROM kv').fetchone()[0]==int(setup.y.sum())
    connection.close()
    mixed=L.Old.make_mixed_stream(setup,.1,1000000,'zipf1.1-10k')
    configs,learning=L.select(setup,scores,256,mixed)
    # This is a genuine suffix after the same250k learning observations, not an
    # early slice that was already seen by the configuration selector.
    tail=mixed[250000:350000]
    results=[]
    methods=[('NoFilter',None),*configs]
    for rep in range(3):
        order=methods[rep:]+methods[:rep]
        for method,c in order:
            con=sqlite3.connect(database);con.execute('PRAGMA cache_size=-8192');con.execute('PRAGMA mmap_size=0');con.execute('PRAGMA query_only=ON')
            exe=L.Executable(setup,X,c,0) if c is not None else None
            if exe:
                for row in mixed[:10]:
                    exe.probe(row)
                exe.insert(np.uint64(setup.h1q[0]));exe.reset() # JIT discarded.
            gets=misses=hits=fn=0
            started=time.perf_counter_ns()
            for row in tail:
                yes=True;h=np.uint64(0)
                if exe:yes,h,_,_=exe.probe(row)
                if yes:
                    key=int(setup.ids[row]).to_bytes(8,'big')
                    value=con.execute('SELECT value FROM kv WHERE key=?',(key,)).fetchone()
                    gets+=1
                    if value is None:
                        misses+=1
                        if exe:exe.insert(h)
                    else:hits+=1
                    assert (value is not None)==bool(setup.y[row])
                elif setup.y[row]:fn+=1
            elapsed=time.perf_counter_ns()-started;assert fn==0
            con.close()
            results.append(dict(dataset='cod',budget_kib=256,method=method,repeat=rep,queries=len(tail),
                                total_ns=elapsed,mean_query_ns=elapsed/len(tail),throughput_qps=len(tail)*1e9/elapsed,
                                backend_gets=gets,backend_misses=misses,backend_hits=hits,false_negatives=fn,
                                selected_trees=c['trees'] if c else 0,selected_frac=c['frac'] if c else 0,
                                state_bytes=c['structure'].used_bytes if c else 0))
            E.save(E.ROOT/'results'/'sqlite_backend.json',dict(rows=results,completed=False,
                scope='Real synchronous SQLite KV gets, with Python/Numba calls and cache feedback; OS cache not flushed; not cold-device latency',
                sqlite_file_bytes=database.stat().st_size,sqlite_page_cache_kib=8192,mmap=False,selection=learning))
            print(f'SQLITE {method} rep{rep} {elapsed/len(tail):.1f}ns gets={gets} misses={misses}',flush=True)
    obj=json.loads((E.ROOT/'results'/'sqlite_backend.json').read_text(encoding='utf-8'));obj['completed']=True;E.save(E.ROOT/'results'/'sqlite_backend.json',obj)
if __name__=='__main__':run()
