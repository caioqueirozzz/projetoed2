// Benchmark: Skip List candidate retrieval vs brute-force, Recall@10 as a
// function of candidate count (plan §15, §16). Emits benchmark_recall.csv.
//
// Dataset : 5000 synthetic 44-dim tracks (uniform random in [0,1], seed 42+i)
// Queries : 100 random tracks drawn from the dataset
// Sweep   : num_candidates ∈ {50, 100, 250, 500, 1000, 2500, 5000}

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <set>
#include <vector>

#include "acoustic_key.hpp"
#include "similarity.hpp"
#include "skip_list.hpp"
#include "track.hpp"

using Clock = std::chrono::high_resolution_clock;

static double elapsedMs(Clock::time_point t0) {
    return std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
}

int main() {
    namespace fs = std::filesystem;
    fs::create_directories("../benchmark/results");

    const int DATASET_SIZE = 5000;
    const int QUERY_COUNT  = 100;
    const int DIMS         = 44;
    const int TOP_K        = 10;

    const std::vector<int> candidateCounts = {50, 100, 250, 500, 1000, 2500, 5000};

    std::cout << "Building " << DATASET_SIZE << " synthetic tracks..." << std::flush;

    ame::AcousticKey keyer(6, 10);
    ame::SkipList    sl;
    std::vector<ame::Track> tracks(DATASET_SIZE);

    for (int i = 0; i < DATASET_SIZE; ++i) {
        std::mt19937 rng(42 + i);
        std::uniform_real_distribution<double> d(0.0, 1.0);

        ame::Track& t = tracks[i];
        t.id = i + 1;
        t.features.resize(DIMS);
        for (int dim = 0; dim < DIMS; ++dim) t.features[dim] = d(rng);
        t.acousticKey = keyer.encode(t.features);
        sl.insert(t.acousticKey, t.id);
    }
    std::cout << " done\n";

    // All track IDs — used as the candidate set for brute-force
    std::vector<int> allIds;
    allIds.reserve(DATASET_SIZE);
    for (const auto& t : tracks) allIds.push_back(t.id);

    // Pick 100 random query indices
    std::mt19937 qrng(42);
    std::uniform_int_distribution<int> qd(0, DATASET_SIZE - 1);
    std::vector<int> queryIdx(QUERY_COUNT);
    for (auto& qi : queryIdx) qi = qd(qrng);

    // Brute-force ground truth (top-10 by exact Euclidean distance)
    std::cout << "Computing brute-force ground truth..." << std::flush;
    std::vector<std::set<int>> groundTruth(QUERY_COUNT);
    for (int qi = 0; qi < QUERY_COUNT; ++qi) {
        const auto& q = tracks[queryIdx[qi]];
        auto results = ame::topK(q.features, tracks, allIds, TOP_K);
        for (const auto& r : results) groundTruth[qi].insert(r.trackId);
    }
    std::cout << " done\n";

    std::ofstream csv("../benchmark/results/benchmark_recall.csv");
    csv << "num_candidates,recall_at_10,avg_query_ms,dataset_size,queries\n";

    for (int numCandidates : candidateCounts) {
        std::cout << "  candidates=" << numCandidates << "..." << std::flush;

        double totalRecall = 0.0;
        double totalMs     = 0.0;

        for (int qi = 0; qi < QUERY_COUNT; ++qi) {
            const auto& q = tracks[queryIdx[qi]];

            auto t0         = Clock::now();
            auto candidates = sl.nearest(q.acousticKey, numCandidates);
            auto results    = ame::topK(q.features, tracks, candidates, TOP_K);
            totalMs        += elapsedMs(t0);

            int hits = 0;
            for (const auto& r : results)
                if (groundTruth[qi].count(r.trackId)) ++hits;
            totalRecall += (double)hits / TOP_K;
        }

        csv << numCandidates << ","
            << totalRecall / QUERY_COUNT << ","
            << totalMs     / QUERY_COUNT << ","
            << DATASET_SIZE << ","
            << QUERY_COUNT  << "\n";

        std::cout << " recall=" << totalRecall / QUERY_COUNT << "\n";
    }

    std::cout << "Wrote benchmark/results/benchmark_recall.csv\n";
    return 0;
}
