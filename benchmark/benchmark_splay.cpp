// Benchmark: Splay Tree vs std::map (BST proxy) (plan §33-§35).
// Two access scenarios:
//   A — uniform distribution      → benchmark_splay_uniform.csv
//   B — locality (80/20 access)   → benchmark_splay_locality.csv
//
// avg_depth reports the mean pre-splay depth (lastDepthBefore) — i.e. how
// deep the node was before being brought to the root. Post-splay depth is
// always 0 by definition; the pre-splay depth reflects access cost.

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <unordered_set>
#include <vector>

#include "splay_tree.hpp"

using Clock = std::chrono::high_resolution_clock;

static double elapsedMs(Clock::time_point t0) {
    return std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
}

struct Row {
    std::string structure;
    int n;
    int accesses;
    double time_ms;
    double avg_depth;
    long long total_rotations;
    double avg_comparisons;
};

static void writeCSV(const std::string& path, const std::vector<Row>& rows) {
    std::ofstream f(path);
    f << "structure,n,accesses,time_ms,avg_depth,total_rotations,avg_comparisons\n";
    for (const auto& r : rows) {
        f << r.structure << "," << r.n << "," << r.accesses << ","
          << r.time_ms << "," << r.avg_depth << ","
          << r.total_rotations << "," << r.avg_comparisons << "\n";
    }
}

int main() {
    namespace fs = std::filesystem;
    fs::create_directories("../benchmark/results");

    const std::vector<int> sizes    = {1000, 5000, 10000, 20000, 50000};
    const int              ACCESSES = 10000;

    std::vector<Row> uniformRows;
    std::vector<Row> localityRows;

    for (int n : sizes) {
        std::cout << "n=" << n << " ..." << std::flush;

        // Build n distinct track IDs: just 1..n (no randomness needed for keys,
        // access patterns drive the splay behavior).
        std::vector<int> ids(n);
        for (int i = 0; i < n; ++i) ids[i] = i + 1;

        // Shuffle so insertion order is random (prevents perfectly balanced BST).
        std::mt19937 rng(42);
        std::shuffle(ids.begin(), ids.end(), rng);

        const int hotSize = std::max(1, n / 5);  // top 20% of IDs

        // ── Build access sequences ────────────────────────────────────────────

        std::vector<int> uniformSeq(ACCESSES);
        {
            std::uniform_int_distribution<int> d(0, n - 1);
            for (auto& v : uniformSeq) v = ids[d(rng)];
        }

        std::vector<int> localitySeq(ACCESSES);
        {
            std::uniform_real_distribution<double> p(0.0, 1.0);
            std::uniform_int_distribution<int> hot(0, hotSize - 1);
            std::uniform_int_distribution<int> cold(hotSize, n - 1);
            for (auto& v : localitySeq)
                v = ids[(p(rng) < 0.8) ? hot(rng) : cold(rng)];
        }

        // ── Scenario A: Uniform ───────────────────────────────────────────────

        // SplayTree — uniform
        {
            ame::SplayTree tree;
            for (int id : ids) tree.insert(id);
            tree.metrics().reset();

            long long depthSum = 0;
            auto t0 = Clock::now();
            for (int id : uniformSeq) {
                tree.access(id);
                depthSum += tree.metrics().lastDepthBefore;
            }
            double ms = elapsedMs(t0);
            auto& m = tree.metrics();
            uniformRows.push_back({
                "SplayTree", n, ACCESSES, ms,
                (double)depthSum / ACCESSES,
                (long long)m.rotations,
                (double)m.comparisons / ACCESSES
            });
        }

        // std::map — uniform
        {
            std::map<int, int> m;
            for (int id : ids) m[id] = 0;

            auto t0 = Clock::now();
            for (int id : uniformSeq) m[id]++;
            double ms = elapsedMs(t0);
            uniformRows.push_back({"StdMap", n, ACCESSES, ms, 0.0, 0, 0.0});
        }

        // ── Scenario B: Locality 80/20 ────────────────────────────────────────

        // SplayTree — locality
        {
            ame::SplayTree tree;
            for (int id : ids) tree.insert(id);
            tree.metrics().reset();

            long long depthSum = 0;
            auto t0 = Clock::now();
            for (int id : localitySeq) {
                tree.access(id);
                depthSum += tree.metrics().lastDepthBefore;
            }
            double ms = elapsedMs(t0);
            auto& m = tree.metrics();
            localityRows.push_back({
                "SplayTree", n, ACCESSES, ms,
                (double)depthSum / ACCESSES,
                (long long)m.rotations,
                (double)m.comparisons / ACCESSES
            });
        }

        // std::map — locality
        {
            std::map<int, int> m;
            for (int id : ids) m[id] = 0;

            auto t0 = Clock::now();
            for (int id : localitySeq) m[id]++;
            double ms = elapsedMs(t0);
            localityRows.push_back({"StdMap", n, ACCESSES, ms, 0.0, 0, 0.0});
        }

        std::cout << " done\n";
    }

    writeCSV("../benchmark/results/benchmark_splay_uniform.csv",  uniformRows);
    writeCSV("../benchmark/results/benchmark_splay_locality.csv", localityRows);
    std::cout << "Wrote benchmark/results/benchmark_splay_uniform.csv\n";
    std::cout << "Wrote benchmark/results/benchmark_splay_locality.csv\n";
    return 0;
}
