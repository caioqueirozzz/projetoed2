// Recall@10 on the processed FMA CSV, with a separately timed exhaustive baseline.
// Run from repository root: build/benchmark_similarity [csv] [output_csv]
// Explicit synthetic demonstration: build/benchmark_similarity --synthetic
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <set>
#include <unordered_map>
#include <vector>

#include "acoustic_key.hpp"
#include "dataset.hpp"
#include "similarity.hpp"
#include "skip_list.hpp"

using Clock = std::chrono::steady_clock;
static double elapsedMs(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

int main(int argc, char** argv) {
    try {
        const bool synthetic = argc > 1 && std::string(argv[1]) == "--synthetic";
        const std::string input = argc > 1 ? argv[1] : "data/processed/tracks_processed.csv";
        const std::filesystem::path output = argc > 2 ? argv[2] :
            (synthetic ? "benchmark/results/benchmark_recall_synthetic.csv" : "benchmark/results/benchmark_recall.csv");
        std::vector<ame::Track> tracks;
        if (synthetic) {
            ame::AcousticKey keyer(6, 10);
            std::mt19937 rng(42);
            std::uniform_real_distribution<double> dist(0, 1);
            for (int i = 0; i < 5000; ++i) {
                ame::Track t;
                t.id = i + 1;
                for (int d = 0; d < 44; ++d) t.features.push_back(dist(rng));
                t.acousticKey = keyer.encode(t.features);
                tracks.push_back(std::move(t));
            }
        } else tracks = ame::loadTracksCsv(input);
        if (tracks.size() < 2) throw std::runtime_error("At least two tracks are required");
        const int count = static_cast<int>(tracks.size());
        const int queries = std::min(100, count);
        const int k = std::min(10, count - 1);
        std::unordered_map<int, std::size_t> trackIndex;
        std::vector<int> allIds;
        ame::SkipList index;
        for (std::size_t i = 0; i < tracks.size(); ++i) {
            trackIndex[tracks[i].id] = i;
            allIds.push_back(tracks[i].id);
            index.insert(tracks[i].acousticKey, tracks[i].id);
        }
        std::mt19937 rng(42);
        std::vector<int> queryIndices;
        for (int i = 0; i < count; ++i) queryIndices.push_back(i);
        std::shuffle(queryIndices.begin(), queryIndices.end(), rng);
        queryIndices.resize(queries);
        std::vector<std::set<int>> truth(queries);
        double bruteMs = 0;
        for (int i = 0; i < queries; ++i) {
            const auto& q = tracks[queryIndices[i]];
            auto start = Clock::now();
            auto candidates = allIds;
            candidates.erase(std::remove(candidates.begin(), candidates.end(), q.id), candidates.end());
            const auto results = ame::topK(q.features, tracks, candidates, k, &trackIndex);
            bruteMs += elapsedMs(start);
            for (const auto& result : results) truth[i].insert(result.trackId);
        }
        if (output.has_parent_path()) std::filesystem::create_directories(output.parent_path());
        std::ofstream csv(output);
        if (!csv) throw std::runtime_error("Cannot write benchmark output");
        csv << "num_candidates,recall_at_10,avg_query_ms,brute_force_ms,dataset_size,queries,top_k,dataset_source\n";
        std::set<int> budgets;
        for (int budget : {50, 100, 250, 500, 1000, 2500, 5000, count - 1})
            budgets.insert(std::min(budget, count - 1));
        for (int budget : budgets) {
            double totalRecall = 0, totalMs = 0;
            for (int i = 0; i < queries; ++i) {
                const auto& q = tracks[queryIndices[i]];
                auto start = Clock::now();
                auto candidates = index.nearest(q.acousticKey, budget + 1);
                candidates.erase(std::remove(candidates.begin(), candidates.end(), q.id), candidates.end());
                if (static_cast<int>(candidates.size()) > budget) candidates.resize(budget);
                auto results = ame::topK(q.features, tracks, candidates, k, &trackIndex);
                totalMs += elapsedMs(start);
                int hits = 0;
                for (const auto& result : results) hits += truth[i].count(result.trackId);
                totalRecall += static_cast<double>(hits) / k;
            }
            csv << budget << ',' << totalRecall / queries << ',' << totalMs / queries << ','
                << bruteMs / queries << ',' << count << ',' << queries << ',' << k << ','
                << (synthetic ? "synthetic" : "processed_csv") << '\n';
            std::cout << "candidates=" << budget << " recall=" << totalRecall / queries << '\n';
        }
        if (!csv) throw std::runtime_error("Failed to write benchmark output");
        std::cout << "Wrote " << output << '\n';
    } catch (const std::exception& error) {
        std::cerr << "Benchmark failed: " << error.what() << '\n';
        return 1;
    }
}
