// Driver for SkiQF / AdaptiveQF variants from github.com/saltsystemslab/SkiRentalAdaptiveQF (commit 28b8b2b).
// Variant headers are used unmodified; core gqf.c/partitioned_counter.c from port/ (arm64 patch only).
// The paper's WiredTiger/SplinterDB reverse maps are replaced by an in-memory map with the same
// key encoding (fingerprint bits << (64-q-r)) + rank; it only recovers original keys.
// usage: skiqf_orig_driver <ski|aqf|hybrid> <budget_bytes> <members.u64> <stream.u64> <learn_n> <breakEven>
// Inputs are 64-bit hashes (QF_KEY_IS_HASH, as in the paper's benchmark).
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <unordered_map>
#include <chrono>
#include "variants/qf_filter.hpp"
#include "variants/skiqf.hpp"
#include "variants/adaptiveqf.hpp"
#include "variants/hybrid_skiqf.hpp"

class MemReverseMap {
public:
  int init(std::string, int qr_bits, int, int, bool clearOld, uint64_t) {
    bits = qr_bits;
    if (clearOld) map.clear();
    return 0;
  }
  uint64_t enc(uint64_t fp, int rank) const {
    uint64_t mask = (1ULL << bits) - 1;
    return ((fp & mask) << (64 - bits)) + rank;
  }
  int insertFingerprint(uint64_t fp, int rank, uint64_t key) { map[enc(fp, rank)] = key; return 0; }
  int insertAndCommitFingerprint(uint64_t fp, int rank, uint64_t key) { map[enc(fp, rank)] = key; return 0; }
  void commitFingerprints() {}
  int getFingerprint(uint64_t fp, int rank, uint64_t *value) {
    auto it = map.find(enc(fp, rank));
    if (it == map.end()) return -1;
    *value = it->second;
    return 0;
  }
  int close() { return 0; }
private:
  int bits = 0;
  std::unordered_map<uint64_t, uint64_t> map;
};

template <class T> static std::vector<T> load(const char *p) {
  FILE *f = std::fopen(p, "rb");
  if (!f) { std::perror(p); std::exit(1); }
  std::fseek(f, 0, SEEK_END);
  size_t n = std::ftell(f) / sizeof(T);
  std::fseek(f, 0, SEEK_SET);
  std::vector<T> v(n);
  if (n && std::fread(v.data(), sizeof(T), n, f) != n) { std::perror("fread"); std::exit(1); }
  std::fclose(f);
  return v;
}

static uint64_t ceil_log2_u64(uint64_t x) { return x <= 1 ? 0 : 64 - __builtin_clzll(x - 1); }

template <class Filter>
static int run(uint64_t budget, std::vector<uint64_t> &members, std::vector<uint64_t> &stream, size_t learn_n, int breakEven) {
  BenchmarkParams params{};
  params.qfConfig.qbits = ceil_log2_u64((uint64_t)(members.size() / 0.95) + 1);
  params.qfConfig.max_load_factor = 0.95;
  params.qfConfig.breakEvenCount = breakEven;
  int rbits = -1;
  uint64_t size = 0;
  for (int r = 56 - (int)params.qfConfig.qbits; r >= 1; r--) {
    params.qfConfig.rbits = r;
    Filter trial;
    if (trial.construct(params)) continue;
    size = trial.sizeInBytes();
    trial.close();
    if (size <= budget) { rbits = r; break; }
  }
  if (rbits < 0) { std::printf("{\"infeasible\": true, \"qbits\": %zu, \"smallest_bytes\": %llu}\n", params.qfConfig.qbits, (unsigned long long)size); return 0; }
  params.qfConfig.rbits = rbits;
  Filter filter;
  filter.construct(params);
  size = filter.sizeInBytes();
  auto t0 = std::chrono::steady_clock::now();
  if (filter.bulkLoad(members.data(), members.size()) < 0) { std::printf("{\"error\": \"insert failed\"}\n"); return 1; }
  size_t fn = 0;
  for (uint64_t k : members) { QFilterQueryResult r{}; filter.queryFilter(k, &r); fn += !r.key_present; }
  uint64_t fp_learn = 0, fp_tail = 0, adapted = 0, rented = 0, failed = 0;
  for (size_t i = 0; i < stream.size(); i++) {
    QFilterQueryResult r{};
    filter.queryFilter(stream[i], &r);
    if (!r.key_present) continue;
    (i < learn_n ? fp_learn : fp_tail)++;
    int ret = filter.adapt(stream[i], &r);
    if (ret < 0) failed++; else if (ret == 0) rented++; else adapted++;
  }
  double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  std::printf("{\"qbits\": %zu, \"rbits\": %d, \"size_bytes\": %llu, \"budget_bytes\": %llu, \"break_even\": %d, "
              "\"member_false_negatives\": %zu, \"fp_learn\": %llu, \"fp_tail\": %llu, \"adapted\": %llu, \"rented\": %llu, "
              "\"adapt_failures\": %llu, \"final_load\": %.4f, \"seconds\": %.2f}\n",
              params.qfConfig.qbits, rbits, (unsigned long long)size, (unsigned long long)budget, breakEven, fn,
              (unsigned long long)fp_learn, (unsigned long long)fp_tail, (unsigned long long)adapted,
              (unsigned long long)rented, (unsigned long long)failed, filter.loadFactor(), secs);
  filter.close();
  return fn != 0;
}

int main(int argc, char **argv) {
  if (argc != 7) { std::fprintf(stderr, "usage: ski|aqf|hybrid budget members stream learn_n breakEven\n"); return 1; }
  std::string kind = argv[1];
  uint64_t budget = std::strtoull(argv[2], nullptr, 10);
  auto members = load<uint64_t>(argv[3]);
  auto stream = load<uint64_t>(argv[4]);
  size_t learn_n = std::strtoull(argv[5], nullptr, 10);
  int breakEven = std::atoi(argv[6]);
  if (kind == "ski") return run<SkiQF<MemReverseMap>>(budget, members, stream, learn_n, breakEven);
  if (kind == "aqf") return run<AdaptiveQF<MemReverseMap>>(budget, members, stream, learn_n, breakEven);
  if (kind == "hybrid") return run<HybridSkiQF<MemReverseMap>>(budget, members, stream, learn_n, breakEven);
  return 1;
}
