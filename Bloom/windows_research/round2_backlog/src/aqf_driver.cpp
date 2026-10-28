// Original AdaptiveQF core; this driver adds strict allocation and reverse-map accounting.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unordered_map>
#include <vector>
#include <malloc.h>
extern "C" {
#include "gqf.h"
#include "gqf_int.h"
void *__real_malloc(size_t); void *__real_calloc(size_t,size_t);void __real_free(void*);
}
static bool tracking=false;static uint64_t filter_bytes=0;
extern "C" void *__wrap_malloc(size_t n){void*p=__real_malloc(n);if(tracking&&p)filter_bytes+=malloc_usable_size(p)+16;return p;}
extern "C" void *__wrap_calloc(size_t n,size_t s){void*p=__real_calloc(n,s);if(tracking&&p)filter_bytes+=malloc_usable_size(p)+16;return p;}
extern "C" void __wrap_free(void*p){__real_free(p);}
static uint64_t aux_live=0,aux_peak=0;
template<class T>struct Alloc{
 using value_type=T;Alloc()=default;template<class U>Alloc(const Alloc<U>&){}
 T*allocate(size_t n){void*p=malloc(n*sizeof(T));if(!p)throw std::bad_alloc();aux_live+=malloc_usable_size(p)+16;aux_peak=std::max(aux_peak,aux_live);return static_cast<T*>(p);}
 void deallocate(T*p,size_t){aux_live-=malloc_usable_size(p)+16;free(p);}
 template<class U>bool operator==(const Alloc<U>&)const{return true;}
 template<class U>bool operator!=(const Alloc<U>&)const{return false;}
};
struct Key{uint64_t fp;int bits;bool operator==(const Key&o)const{return fp==o.fp&&bits==o.bits;}};
struct Hash{size_t operator()(const Key&k)const{uint64_t x=k.fp^(uint64_t(k.bits)*0x9e3779b97f4a7c15ULL);x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;return x;}};
using Pair=std::pair<const Key,uint64_t>;
using Map=std::unordered_map<Key,uint64_t,Hash,std::equal_to<Key>,Alloc<Pair>>;
template<class T>std::vector<T>read(const char*path){std::ifstream f(path,std::ios::binary|std::ios::ate);if(!f)throw std::runtime_error(path);auto n=f.tellg();std::vector<T>a(size_t(n)/sizeof(T));f.seekg(0);f.read((char*)a.data(),n);return a;}
static constexpr uint8_t flags=QF_KEY_IS_HASH|QF_NO_LOCK;
static Key query(QF&q,uint64_t h,uint64_t&index,bool&hit){uint64_t fp=0;int bits=0;hit=qf_query(&q,h,&index,&fp,&bits,flags)>0;return Key{fp,bits};}
static void cleanup(QF&q){pc_destructor(&q.runtimedata->pc_nelts);pc_destructor(&q.runtimedata->pc_ndistinct_elts);pc_destructor(&q.runtimedata->pc_noccupied_slots);qf_free(&q);}
int main(int argc,char**argv){try{
 if(argc!=7)throw std::runtime_error("budget_bytes members.u64 queries.u64 stream.i64 tail_start output.json");
 uint64_t budget=std::stoull(argv[1]),tail=std::stoull(argv[5]);
 auto members=read<uint64_t>(argv[2]),queries=read<uint64_t>(argv[3]);auto stream=read<int64_t>(argv[4]);
 uint64_t slots=64;int qbits=6;while(double(members.size())/slots>.90){slots*=2;qbits++;}
 int chosen=0;uint64_t chosen_bytes=0;
 for(int r=2;r<=24;r++){QF test{};filter_bytes=sizeof(QF);tracking=true;bool ok=qf_malloc(&test,slots,qbits+r,0,QF_HASH_NONE,17);tracking=false;if(!ok)throw std::runtime_error("allocation");uint64_t used=filter_bytes;cleanup(test);if(used<=budget){chosen=r;chosen_bytes=used;}}
 if(!chosen){std::ofstream(argv[6])<<"{\"feasible\":false,\"reason\":\"minimum real AQF allocation exceeds budget\"}";return 0;}
 QF q{};filter_bytes=sizeof(QF);tracking=true;qf_malloc(&q,slots,qbits+chosen,0,QF_HASH_NONE,17);tracking=false;
 Map reverse;reverse.reserve(members.size()*1.2);
 uint64_t collisions=0;
 for(auto h:members){uint64_t index;bool hit;Key k=query(q,h,index,hit);
  if(hit){auto it=reverse.find(k);if(it==reverse.end())throw std::runtime_error("construction reverse map missing");uint64_t old=it->second,ret_new=0,ret_old=0;reverse.erase(it);if(old==h)throw std::runtime_error("duplicate member hash");
   if(qf_get_num_occupied_slots(&q)+34>=uint64_t(slots*.95))throw std::runtime_error("construction capacity");
   insert_and_extend(&q,index,h,1,old,&ret_new,&ret_old,flags);bool ok;uint64_t ix;Key ko=query(q,old,ix,ok);if(!ok)throw std::runtime_error("member lost in construction");reverse[ko]=old;collisions++;
  }else{uint64_t fp;int bits;if(qf_insert_ret(&q,h,1,&index,&fp,&bits,flags)<0)throw std::runtime_error("insert failed");}
  bool ok;uint64_t ix;Key kh=query(q,h,ix,ok);if(!ok)throw std::runtime_error("new member missing");reverse[kh]=h;
 }
 uint64_t fn_before=0,fn_after=0;for(auto h:members){bool ok;uint64_t ix;query(q,h,ix,ok);fn_before+=!ok;}
 uint64_t fp_full=0,fp_tail=0,adaptations=0,skipped=0;
 for(size_t i=0;i<stream.size();i++){uint64_t h=queries.at(stream[i]),ix;bool hit;Key k=query(q,h,ix,hit);if(!hit)continue;fp_full++;fp_tail+=(i>=tail);
  auto it=reverse.find(k);if(it==reverse.end())throw std::runtime_error("adapt reverse map missing");uint64_t original=it->second;
  if(original==h){skipped++;continue;}int low=__builtin_ctzll(original^h);int need=std::max(1,(low+1-k.bits+chosen-1)/chosen);
  if(qf_get_num_occupied_slots(&q)+need>=uint64_t(slots*.94)){skipped++;continue;}
  uint64_t ret=0;int rc=qf_adapt(&q,ix,original,h,&ret,flags);if(rc<0)throw std::runtime_error("adapt failed");reverse.erase(it);
  bool ok;Key next=query(q,original,ix,ok);if(!ok)throw std::runtime_error("member lost adapting");reverse[next]=original;adaptations++;
 }
 for(auto h:members){bool ok;uint64_t ix;query(q,h,ix,ok);fn_after+=!ok;}
 std::ofstream out(argv[6]);out<<"{\"feasible\":true,\"budget_bytes\":"<<budget<<",\"filter_allocated_bytes\":"<<filter_bytes<<",\"reverse_map_allocated_bytes\":"<<aux_live<<",\"reverse_map_peak_bytes\":"<<aux_peak<<",\"slots\":"<<slots<<",\"remainder_bits\":"<<chosen<<",\"fp_full\":"<<fp_full<<",\"fp_tail\":"<<fp_tail<<",\"adaptations\":"<<adaptations<<",\"skipped_adaptations\":"<<skipped<<",\"construction_collisions\":"<<collisions<<",\"fn_before\":"<<fn_before<<",\"fn_after\":"<<fn_after<<"}";
 cleanup(q);if(fn_before||fn_after||filter_bytes>budget)return 2;return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
