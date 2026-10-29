// Driver for the official AdaptiveQF (github.com/splatlab/adaptiveqf, commit 6a6ca59) through its
// C++ wrapper AdaptiveQF<LocalMap>; core sources compiled from port/ (arm64 patch only, port.patch).
// usage: aqf_orig_driver <budget_bytes> <members.u64> <stream.u64> <learn_n>
// Every stream key is a non-member, so every positive answer is a false positive and is adapted.
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <chrono>
#include "aqf_wrapper.hpp"
#include "localmap_db.hpp"

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

int main(int argc, char **argv) {
    if (argc != 5) { std::fprintf(stderr, "usage: budget members stream learn_n\n"); return 1; }
    uint64_t budget = std::strtoull(argv[1], nullptr, 10);
    auto members = load<uint64_t>(argv[2]);
    auto stream = load<uint64_t>(argv[3]);
    size_t learn_n = std::strtoull(argv[4], nullptr, 10);
    const double load = 0.95;
    AdaptiveQF<LocalMap> filter;
    int rbits = -1;
    uint64_t size = 0;
    for (int r = 56; r >= 1; r--) {   // largest remainder whose filter fits the budget
        AdaptiveQF<LocalMap> trial;
        if (trial.initializeForCapacity(members.size(), r, load, QF_HASH_DEFAULT)) continue;
        size = trial.sizeInBytes();
        trial.close();
        if (size <= budget) { rbits = r; break; }
    }
    if (rbits < 0) { std::printf("{\"infeasible\": true, \"smallest_bytes\": %llu}\n", (unsigned long long)size); return 0; }
    filter.initializeForCapacity(members.size(), rbits, load, QF_HASH_DEFAULT);
    size = filter.sizeInBytes();
    auto t0 = std::chrono::steady_clock::now();
    if (filter.bulkInsert(members.data(), members.size()) < 0) { std::printf("{\"error\": \"insert failed\"}\n"); return 1; }
    size_t fn = 0;
    for (uint64_t k : members) { QFilterQueryResult r; filter.queryFilter(k, &r); fn += !r.key_present; }
    uint64_t fp_learn = 0, fp_tail = 0, adapt_fail = 0;
    for (size_t i = 0; i < stream.size(); i++) {
        QFilterQueryResult r;
        filter.queryFilter(stream[i], &r);
        if (!r.key_present) continue;
        (i < learn_n ? fp_learn : fp_tail)++;
        if (filter.adapt(stream[i], &r) < 0) adapt_fail++;
    }
    double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    std::printf("{\"rbits\": %d, \"size_bytes\": %llu, \"budget_bytes\": %llu, \"member_false_negatives\": %zu, "
                "\"fp_learn\": %llu, \"fp_tail\": %llu, \"adapt_failures\": %llu, \"final_load\": %.4f, \"seconds\": %.2f}\n",
                rbits, (unsigned long long)size, (unsigned long long)budget, fn, (unsigned long long)fp_learn,
                (unsigned long long)fp_tail, (unsigned long long)adapt_fail, filter.loadFactor(), secs);
    filter.close();
    return fn != 0;
}
