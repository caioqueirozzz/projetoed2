// Benchmark: Skip List vs sorted vector + binary_search vs std::map (plan §32).
// Emits benchmark_skiplist.csv into benchmark/results/.
//
// Dataset sizes: 1k, 5k, 10k, 15k, 20k, 25k
// Operations   : insert, search (hit), remove, nearest (SkipList only)
// Metrics      : time_ms, comparisons

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <vector>

#include "skip_list.hpp"

using Clock = std::chrono::high_resolution_clock;

static double elapsedMs(Clock::time_point t0) {
    return std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
}

int main() {
    namespace fs = std::filesystem;
    fs::create_directories("../benchmark/results");

    std::ofstream csv("../benchmark/results/benchmark_skiplist.csv");
    csv << "structure,n,operation,time_ms,comparisons\n";

    const std::vector<int> sizes = {1000, 5000, 10000, 15000, 20000, 25000};
    const int EXTRA = 100;  // keys used for search / remove queries

    for (int n : sizes) {
        std::cout << "n=" << n << " ..." << std::flush;

        // Generate n + EXTRA random uint64_t keys (deterministic, seed 42).
        std::mt19937_64 rng(42);
        std::uniform_int_distribution<std::uint64_t> dist(1, UINT64_MAX);

        std::vector<std::uint64_t> keys;
        keys.reserve(n + EXTRA);
        for (int i = 0; i < n + EXTRA; ++i) keys.push_back(dist(rng));

        // keys[0..n-1]        → inserted into each structure
        // keys[n..n+EXTRA-1]  → used as query keys for nearest

        // ── Skip List ─────────────────────────────────────────────────────────
        {
            ame::SkipList sl;

            // insert
            sl.metrics().reset();
            auto t0 = Clock::now();
            for (int i = 0; i < n; ++i) sl.insert(keys[i], i);
            double ins_ms  = elapsedMs(t0);
            long long ins_cmp = (long long)sl.metrics().comparisons;
            csv << "SkipList," << n << ",insert," << ins_ms << "," << ins_cmp << "\n";

            // search (hit: first EXTRA inserted keys)
            sl.metrics().reset();
            t0 = Clock::now();
            for (int i = 0; i < EXTRA; ++i) sl.search(keys[i]);
            double srch_ms  = elapsedMs(t0);
            long long srch_cmp = (long long)sl.metrics().comparisons;
            csv << "SkipList," << n << ",search," << srch_ms << "," << srch_cmp << "\n";

            // nearest — 100 queries with fresh keys not in the list
            sl.metrics().reset();
            t0 = Clock::now();
            for (int i = n; i < n + EXTRA; ++i) sl.nearest(keys[i], 100);
            double near_ms  = elapsedMs(t0);
            long long near_cmp = (long long)sl.metrics().comparisons;
            csv << "SkipList," << n << ",nearest," << near_ms << "," << near_cmp << "\n";

            // remove (same first EXTRA keys, trackId = their index)
            sl.metrics().reset();
            t0 = Clock::now();
            for (int i = 0; i < EXTRA; ++i) sl.remove(keys[i], i);
            double rem_ms  = elapsedMs(t0);
            long long rem_cmp = (long long)sl.metrics().comparisons;
            csv << "SkipList," << n << ",remove," << rem_ms << "," << rem_cmp << "\n";
        }

        // ── Sorted vector (insertion-sort style, binary-search lookup) ────────
        {
            std::vector<std::uint64_t> vec;
            vec.reserve(n);

            long long ins_cmp = 0;
            auto t0 = Clock::now();
            for (int i = 0; i < n; ++i) {
                auto pos = std::lower_bound(vec.begin(), vec.end(), keys[i]);
                // binary search visits ≈ log2(current size + 1) nodes
                int sz = (int)vec.size();
                ins_cmp += (sz > 0) ? (long long)std::ceil(std::log2(sz + 1)) : 0;
                vec.insert(pos, keys[i]);
            }
            double ins_ms = elapsedMs(t0);
            csv << "SortedVector," << n << ",insert," << ins_ms << "," << ins_cmp << "\n";

            long long srch_cmp = 0;
            t0 = Clock::now();
            for (int i = 0; i < EXTRA; ++i) {
                std::lower_bound(vec.begin(), vec.end(), keys[i]);
                srch_cmp += (long long)std::ceil(std::log2((int)vec.size() + 1));
            }
            double srch_ms = elapsedMs(t0);
            csv << "SortedVector," << n << ",search," << srch_ms << "," << srch_cmp << "\n";

            long long rem_cmp = 0;
            t0 = Clock::now();
            for (int i = 0; i < EXTRA; ++i) {
                auto pos = std::lower_bound(vec.begin(), vec.end(), keys[i]);
                rem_cmp += (long long)std::ceil(std::log2((int)vec.size() + 1));
                if (pos != vec.end() && *pos == keys[i]) vec.erase(pos);
            }
            double rem_ms = elapsedMs(t0);
            csv << "SortedVector," << n << ",remove," << rem_ms << "," << rem_cmp << "\n";
        }

        // ── std::map (RB-tree; comparisons approximated as log2(n)) ──────────
        {
            std::map<std::uint64_t, int> m;

            auto t0 = Clock::now();
            for (int i = 0; i < n; ++i) m.emplace(keys[i], i);
            double ins_ms = elapsedMs(t0);
            long long ins_cmp = n > 1 ? (long long)(n * std::log2(n)) : 0;
            csv << "StdMap," << n << ",insert," << ins_ms << "," << ins_cmp << "\n";

            long long per_query = n > 1 ? (long long)std::ceil(std::log2(n)) : 1;

            t0 = Clock::now();
            for (int i = 0; i < EXTRA; ++i) m.find(keys[i]);
            double srch_ms = elapsedMs(t0);
            csv << "StdMap," << n << ",search," << srch_ms << "," << EXTRA * per_query << "\n";

            t0 = Clock::now();
            for (int i = 0; i < EXTRA; ++i) m.erase(keys[i]);
            double rem_ms = elapsedMs(t0);
            csv << "StdMap," << n << ",remove," << rem_ms << "," << EXTRA * per_query << "\n";
        }

        std::cout << " done\n";
    }

    std::cout << "Wrote benchmark/results/benchmark_skiplist.csv\n";
    return 0;
}
