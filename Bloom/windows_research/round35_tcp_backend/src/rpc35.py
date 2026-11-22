"""Bounded binary localhost RPC. No labels, model outputs or SQL text are sent."""
import json
import socket
import struct

GET=1
GET_PREFIX=2
RESET=3
STATS=4
STOP=5
PING=6
ABSENT=0
FOUND=1
ACK=2
STATISTICS=3
ERROR=4
REQUEST=struct.Struct('!Bq')
HEADER=struct.Struct('!BBHI')
MAX_PAYLOAD=16384
VALUE=b'\0'*32


class ProtocolError(RuntimeError):pass


def recv_exact(sock,n,allow_clean_eof=False):
    chunks=[];remaining=n
    while remaining:
        part=sock.recv(remaining)
        if not part:
            if allow_clean_eof and remaining==n:return None
            raise ProtocolError('Truncated TCP frame')
        chunks.append(part);remaining-=len(part)
    return b''.join(chunks)


def send_reply(sock,status,prefix=0,payload=b''):
    if not 0<=prefix<=65 or len(payload)>MAX_PAYLOAD:raise ProtocolError('Invalid reply fields')
    sock.sendall(HEADER.pack(status,prefix,0,len(payload))+payload)


class Client:
    def __init__(self,host,port,timeout=30):
        if host!='127.0.0.1':raise ValueError('This protocol is restricted to an explicitly local benchmark')
        self.sock=socket.create_connection((host,port),timeout=timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);self.sock.settimeout(timeout)
        self.reset_query_counters()

    def reset_query_counters(self):
        self.sql_calls=0;self.query_sent_bytes=0;self.query_received_bytes=0

    def request(self,op,key=0):
        self.sock.sendall(REQUEST.pack(op,int(key)))
        header=recv_exact(self.sock,HEADER.size);status,prefix,reserved,size=HEADER.unpack(header)
        if reserved or prefix>65 or size>MAX_PAYLOAD:raise ProtocolError('Invalid response header')
        payload=recv_exact(self.sock,size)
        if status==ERROR:raise ProtocolError('Server rejected request: '+payload.decode('ascii',errors='replace'))
        return status,prefix,payload

    def get(self,key,need_prefix):
        status,prefix,payload=self.request(GET_PREFIX if need_prefix else GET,key)
        self.sql_calls+=1;self.query_sent_bytes+=REQUEST.size;self.query_received_bytes+=HEADER.size+len(payload)
        if status==FOUND:
            if prefix!=0 or payload!=VALUE:raise ProtocolError('Invalid found payload')
            return True,0,len(payload)
        if status!=ABSENT or payload:raise ProtocolError('Invalid absent payload')
        if (need_prefix and not 1<=prefix<=65) or (not need_prefix and prefix!=0):raise ProtocolError('Missing/unexpected verified-prefix response')
        return False,prefix,0

    def reset(self):
        s,l,p=self.request(RESET)
        if (s,l,p)!=(ACK,0,b''):raise ProtocolError('Invalid reset acknowledgement')
        self.reset_query_counters()

    def stats(self):
        s,l,p=self.request(STATS)
        if s!=STATISTICS or l:raise ProtocolError('Invalid statistics reply')
        return json.loads(p)

    def ping(self):
        if self.request(PING)!=(ACK,0,b'pong'):raise ProtocolError('Invalid ping')

    def shutdown(self):
        if self.request(STOP)!=(ACK,0,b''):raise ProtocolError('Invalid shutdown acknowledgement')

    def close(self):self.sock.close()
