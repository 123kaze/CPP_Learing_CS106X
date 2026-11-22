"""SQLite service on127.0.0.1. The safety index is backend-owned and queried only after SQL absence."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(WR/'round31_sqlite_online/src'))
from rpc35 import *
from online31 import E5,J,np
from numba import njit,get_num_threads
import sqlite3,time,resource,ctypes


@njit(cache=True)
def hash_key(key):
    z=(np.uint64(key)^np.uint64(0xA5A50001))+np.uint64(0x9E3779B97F4A7C15)
    z=(z^(z>>np.uint64(30)))*np.uint64(0xBF58476D1CE4E5B9)
    z=(z^(z>>np.uint64(27)))*np.uint64(0x94D049BB133111EB)
    return z^(z>>np.uint64(31))


@njit(cache=True)
def prefix_for_key(sorted_hashes,key):return J.safe_len(sorted_hashes,hash_key(key))


def serve_connection(conn,con,member_hashes,max_sql=2000000):
    conn.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);conn.settimeout(180)
    cur=con.cursor();total=0
    counts=dict(sql_calls=0,found=0,absent=0,prefix_queries=0)
    wall=time.perf_counter_ns();cpu=time.process_time_ns()
    try:
        while True:
            frame=recv_exact(conn,REQUEST.size,allow_clean_eof=True)
            if frame is None:break
            op,key=REQUEST.unpack(frame)
            if op in (GET,GET_PREFIX):
                if total>=max_sql:send_reply(conn,ERROR,payload=b'query-limit');break
                # Authoritative SQL always precedes any safety-index computation.
                row=cur.execute('SELECT value FROM kv WHERE key = ?',(key,)).fetchone()
                total+=1;counts['sql_calls']+=1
                if row is not None:
                    counts['found']+=1;send_reply(conn,FOUND,payload=row[0])
                else:
                    counts['absent']+=1;length=0
                    if op==GET_PREFIX:
                        counts['prefix_queries']+=1;length=int(prefix_for_key(member_hashes,np.int64(key)))
                    send_reply(conn,ABSENT,prefix=length)
            elif key!=0:send_reply(conn,ERROR,payload=b'invalid-control-key')
            elif op==RESET:
                counts=dict(sql_calls=0,found=0,absent=0,prefix_queries=0);wall=time.perf_counter_ns();cpu=time.process_time_ns();send_reply(conn,ACK)
            elif op==STATS:
                value=dict(counts,total_sql_calls=total,elapsed_since_reset_ns=time.perf_counter_ns()-wall,cpu_since_reset_ns=time.process_time_ns()-cpu,
                           peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                send_reply(conn,STATISTICS,payload=json.dumps(value,separators=(',',':')).encode())
            elif op==PING:send_reply(conn,ACK,payload=b'pong')
            elif op==STOP:send_reply(conn,ACK);break
            else:send_reply(conn,ERROR,payload=b'unknown-opcode')
    finally:cur.close()
    return total


def main(ds,path):
    from worker31 import SETTINGS
    if ds not in SETTINGS:raise ValueError('Unknown dataset')
    if path.exists():raise FileExistsError('Refuse existing database')
    lib=ctypes.CDLL(str(Path(sys.prefix)/'lib/libopenblas.0.dylib'));f=lib.openblas_get_num_threads;f.restype=ctypes.c_int;assert f()==get_num_threads()==1
    start=time.perf_counter()
    with np.load(E5.C.CACHE/ds/'data.npz',allow_pickle=False) as d:ids,y=d['ids'],d['y']
    members=ids[y].copy();n=len(members);assert 0<n<=3000000
    timer=time.perf_counter();member_hashes=np.sort(E5.C.splitmix64(members^np.uint64(E5.C.H1_SALT)));index_s=time.perf_counter()-timer
    signed=members.view(np.int64);warm_key=int(signed[0])
    timer=time.perf_counter();con=sqlite3.connect(str(path));con.execute('CREATE TABLE kv (key INTEGER PRIMARY KEY, value BLOB NOT NULL)')
    con.executemany('INSERT INTO kv VALUES (?,?)',((int(k),VALUE) for k in signed));con.commit();assert con.execute('SELECT COUNT(*) FROM kv').fetchone()[0]==n
    db_s=time.perf_counter()-timer
    info=dict(dataset=ds,members=n,database_build_s=db_s,index_build_s=index_s,index_payload_bytes=member_hashes.nbytes,index_physical_bytes=sys.getsizeof(member_hashes),
              page_count=con.execute('PRAGMA page_count').fetchone()[0],page_size=con.execute('PRAGMA page_size').fetchone()[0],cache_size=con.execute('PRAGMA cache_size').fetchone()[0],
              journal_mode=con.execute('PRAGMA journal_mode').fetchone()[0],sqlite_version=sqlite3.sqlite_version,native_threads=1,host='127.0.0.1',tcp_nodelay=True)
    del ids,y,members,signed
    timer=time.perf_counter();assert prefix_for_key(member_hashes,np.int64(warm_key))==65
    for _ in range(2000):assert con.execute('SELECT value FROM kv WHERE key = ?',(warm_key,)).fetchone()==(VALUE,)
    info['warm_and_compile_s']=time.perf_counter()-timer
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(180)
        info.update(event='ready',port=listener.getsockname()[1],pid=os.getpid(),startup_s=time.perf_counter()-start)
        print(json.dumps(info),flush=True)
        conn,_=listener.accept()
        with conn:total=serve_connection(conn,con,member_hashes)
    con.close();print(json.dumps(dict(event='stopped',total_sql_calls=total)),flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('database',type=Path);a=p.parse_args();main(a.dataset,a.database)
