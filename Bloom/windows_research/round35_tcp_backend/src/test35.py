import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rpc35 import *
from backend35 import hash_key,prefix_for_key,serve_connection,E5,np
from client35 import RpcFilter,online_rpc
from online31 import B,K,probe_bf
from types import SimpleNamespace
import unittest,threading,queue,sqlite3


class Prepared:
    @property
    def sorted_members(self):raise AssertionError('Client attempted to acquire member index')
    @property
    def member(self):raise AssertionError('Client attempted to acquire labels')


class Tests(unittest.TestCase):
    def fixture_server(self):
        ready=queue.Queue();errors=[]
        def server():
            con=sqlite3.connect(':memory:')
            try:
                con.execute('create table kv(key integer primary key,value blob not null)');con.executemany('insert into kv values(?,?)',[(1,VALUE),(2,VALUE)]);con.commit()
                hashes=np.sort(E5.C.splitmix64(np.array([1,2],np.uint64)^np.uint64(E5.C.H1_SALT)))
                with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
                    listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(10);ready.put(listener.getsockname()[1])
                    conn,_=listener.accept()
                    with conn:serve_connection(conn,con,hashes,max_sql=100)
            except Exception as e:errors.append(repr(e))
            finally:con.close()
        thread=threading.Thread(target=server,daemon=True);thread.start();port=ready.get(timeout=15);client=Client('127.0.0.1',port)
        def cleanup():
            try:client.shutdown()
            except Exception:pass
            client.close();thread.join(timeout=10);self.assertFalse(thread.is_alive());self.assertFalse(errors,errors)
        self.addCleanup(cleanup);return client

    def test_signed_key_hash_exactly_matches_frozen_vector_hash(self):
        rng=np.random.default_rng(35);ids=np.concatenate([np.array([0,1,2**63,2**64-1],np.uint64),rng.integers(0,np.iinfo(np.uint64).max,128,dtype=np.uint64)])
        expected=E5.C.splitmix64(ids^np.uint64(E5.C.H1_SALT));actual=np.array([hash_key(k) for k in ids.view(np.int64)],np.uint64)
        np.testing.assert_array_equal(expected,actual)
        members=np.sort(expected[:3])
        for key,h in zip(ids.view(np.int64),expected):self.assertEqual(prefix_for_key(members,key),E5.E.CC.safe_prefix_lengths(members,np.array([h],np.uint64))[0])

    def test_SQL_presence_and_selective_prefix_work(self):
        client=self.fixture_server();client.ping();client.reset()
        self.assertEqual(client.get(3,False),(False,0,0));self.assertEqual(client.get(3,False),(False,0,0))
        self.assertEqual(client.stats()['prefix_queries'],0)
        exists,length,n=client.get(3,True);self.assertFalse(exists);self.assertTrue(1<=length<=65);self.assertEqual(n,0)
        self.assertEqual(client.get(1,True),(True,0,32))
        stats=client.stats();self.assertEqual((stats['sql_calls'],stats['found'],stats['absent'],stats['prefix_queries']),(4,1,3,1))

    def test_no_index_client_caches_only_after_TCP_absence(self):
        client=self.fixture_server();ids=np.array([1,3,2],np.uint64);h=E5.C.splitmix64(ids^np.uint64(E5.C.H1_SALT))
        spec=K.layout(512);bf=B.allocate(2,4096,spec['allocated_bytes']);bf[B.HEAD_WORDS:]=np.uint64(0xffffffffffffffff)
        p=Prepared();p.hashes=h;p.spec=spec;p.is_learned=False;p.impl=probe_bf;p.base_args=(h,bf);p.c=dict(cache_bytes=spec['allocated_bytes'],structure=SimpleNamespace(data=bf))
        flt=RpcFilter(p);before=flt.data.copy();self.assertEqual(flt.probe(1),1);np.testing.assert_array_equal(flt.data,before)
        self.assertFalse(hasattr(flt,'sorted_members'));client.reset();mask=np.zeros(5,np.uint8)
        r=online_rpc(client,ids.view(np.int64),np.array([1,1,0,2,1],np.int64),flt,mask)
        np.testing.assert_array_equal(mask,[1,0,1,1,0]);self.assertEqual((r['backend_calls'],r['fp'],r['members_found'],r['cache_hits']),(3,1,2,2))
        self.assertEqual(client.stats()['prefix_queries'],1)

    def test_unknown_opcode_does_not_execute_SQL(self):
        client=self.fixture_server();client.reset()
        with self.assertRaises(ProtocolError):client.request(255)
        self.assertEqual(client.stats()['sql_calls'],0);client.ping()

    def test_truncated_and_oversized_frames_rejected(self):
        class Fake:
            def __init__(self,data):self.data=data
            def recv(self,n):p=self.data[:n];self.data=self.data[n:];return p
            def sendall(self,data):pass
        with self.assertRaises(ProtocolError):recv_exact(Fake(b'x'),2)
        self.assertIsNone(recv_exact(Fake(b''),2,allow_clean_eof=True))
        client=Client.__new__(Client);client.sock=Fake(HEADER.pack(FOUND,0,0,MAX_PAYLOAD+1))
        with self.assertRaises(ProtocolError):client.request(GET,1)


if __name__=='__main__':unittest.main()
