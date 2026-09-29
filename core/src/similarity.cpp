#include "similarity.hpp"

#include <algorithm>
#include <cmath>
#include <queue>
#include <unordered_map>

namespace ame {

double squaredEuclidean(const std::vector<double>& a, const std::vector<double>& b) {
    double sum = 0.0;
    const std::size_t n = a.size() < b.size() ? a.size() : b.size();
    for (std::size_t i = 0; i < n; ++i) {
        const double d = a[i] - b[i];
        sum += d * d;
    }
    return sum;
}

double euclidean(const std::vector<double>& a, const std::vector<double>& b) {
    return std::sqrt(squaredEuclidean(a, b));
}

// ── topK ──────────────────────────────────────────────────────────────────────
//
// Rank `candidateIds` against `query` and return the K closest (plan §14).
//
// Algorithm (bounded max-heap, O(C log K) where C = |candidateIds|):
//   1. Reuse the supplied ID index, or build an O(N) local map if absent.
//   2. For each candidate, compute squaredEuclidean (cheaper than sqrt, and
//      monotonic so it ranks identically).
//   3. Keep a max-heap of at most K entries. The top is always the worst
//      (largest) distance seen so far. When a better candidate arrives, evict
//      the top and push the new entry.
//   4. Drain the heap (largest-first), convert to real Euclidean distances,
//      reverse → results sorted ascending (closest first).
//
// Unknown candidateIds (not present in `tracks`) are silently skipped so the
// function is robust to stale IDs from an older Skip List index.

std::vector<SimilarityResult> topK(const std::vector<double>& query,
                                    const std::vector<Track>& tracks,
                                    const std::vector<int>& candidateIds,
                                    std::size_t k,
                                    const std::unordered_map<int, std::size_t>* trackIndex) {
    if (k == 0 || candidateIds.empty() || tracks.empty()) return {};

    // Applications/benchmarks reuse their index; standalone callers may omit it.
    std::unordered_map<int, std::size_t> idToIdx;
    if (!trackIndex) {
        idToIdx.reserve(tracks.size());
        for (std::size_t i = 0; i < tracks.size(); ++i)
            idToIdx[tracks[i].id] = i;
        trackIndex = &idToIdx;
    }

    // Max-heap: pair<squaredDistance, trackId> — largest distance on top.
    using Entry = std::pair<double, int>;
    std::priority_queue<Entry> heap;

    for (const int id : candidateIds) {
        const auto it = trackIndex->find(id);
        if (it == trackIndex->end()) continue;

        const double d2 = squaredEuclidean(query, tracks[it->second].features);

        if (heap.size() < k) {
            heap.emplace(d2, id);
        } else if (Entry{d2, id} < heap.top()) {
            heap.pop();
            heap.emplace(d2, id);
        }
    }

    // Drain heap (largest-first) and convert squared → real distance.
    std::vector<SimilarityResult> results;
    results.reserve(heap.size());
    while (!heap.empty()) {
        results.push_back({heap.top().second, std::sqrt(heap.top().first)});
        heap.pop();
    }
    std::reverse(results.begin(), results.end());   // closest first

    return results;
}

}  // namespace ame
