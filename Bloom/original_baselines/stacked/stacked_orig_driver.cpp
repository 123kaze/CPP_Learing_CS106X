// Driver for the original Stacked Filter (bitbucket.org/HarvardDASlab/stackedfilters, commit 6e04ca6),
// Bloom layers, 64-bit BigIntElement keys. The library headers are used unmodified.
// usage: stacked_orig_driver <total_bits> <positives.u64> <negatives.u64> <cdf.f64> <queries.u64> <out.u8>
// negatives in descending learning frequency, cdf = cumulative query share (as in the README).
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <chrono>
#include "StackedFilter.h"

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

static std::vector<BigIntElement> elements(const std::vector<uint64_t> &raw) {
    std::vector<BigIntElement> out;
    out.reserve(raw.size());
    for (uint64_t x : raw) out.emplace_back((long int)x);
    return out;
}

int main(int argc, char **argv) {
    if (argc != 7) { std::fprintf(stderr, "usage: total_bits pos neg cdf queries out\n"); return 1; }
    size_t total_bits = std::strtoull(argv[1], nullptr, 10);
    auto pos = elements(load<uint64_t>(argv[2]));
    auto neg = elements(load<uint64_t>(argv[3]));
    auto cdf = load<double>(argv[4]);
    auto qry = load<uint64_t>(argv[5]);
    auto t0 = std::chrono::steady_clock::now();
    StackedFilter<BloomFilterLayer, BigIntElement> filter(total_bits, pos, neg, cdf);
    double build_s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    size_t fn = 0;
    for (const auto &p : pos) fn += !filter.LookupElement(p);
    std::vector<uint8_t> out(qry.size());
    size_t fp = 0;
    for (size_t i = 0; i < qry.size(); i++) fp += (out[i] = filter.LookupElement(BigIntElement((long int)qry[i])));
    FILE *f = std::fopen(argv[6], "wb");
    std::fwrite(out.data(), 1, out.size(), f);
    std::fclose(f);
    std::printf("{\"total_bits\": %zu, \"actual_bits\": %zu, \"layers\": %u, \"member_false_negatives\": %zu, "
                "\"query_fp\": %zu, \"queries\": %zu, \"build_seconds\": %.3f}\n",
                total_bits, filter.GetSize(), filter.num_layers_, fn, fp, qry.size(), build_s);
    return fn != 0;
}
