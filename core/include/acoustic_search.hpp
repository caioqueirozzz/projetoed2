#pragma once
#include "skip_list.hpp"
#include "similarity.hpp"
#include <unordered_map>

namespace ame {
struct SearchReport {
    std::vector<SimilarityResult> results;
    std::size_t candidates = 0, initialCandidates = 0, pruned = 0, visited = 0;
    std::uint64_t comparisons = 0;
    double indexMs = 0, similarityMs = 0, totalMs = 0;
    double recall = -1, bruteMs = 0;
    bool exact = false;
};
// Two Skip Lists: Morton windows and an outward metric search ordered by
// distance to a pivot. Triangle-inequality lower bounds certify pruning.
class AcousticSearch {
public:
    explicit AcousticSearch(std::vector<Track> tracks, unsigned seed = 42);
    SearchReport search(int queryId, int budget, int k, bool exact, bool evaluate = false);
    const Track& track(int id) const;
    const std::vector<Track>& tracks() const { return tracks_; }
    SkipList& morton() { return morton_; }
private:
    std::vector<Track> tracks_;
    std::unordered_map<int, std::size_t> ids_;
    SkipList morton_, radial_;
    std::vector<std::uint64_t> seen_;
    std::uint64_t epoch_ = 0;
    std::vector<std::vector<double>> pivotDistances_;
    static std::uint64_t radialKey(double distance);
};
}
