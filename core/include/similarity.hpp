#pragma once

#include <cstddef>
#include <vector>
#include <unordered_map>

#include "track.hpp"

namespace ame {

/// A scored search result: which track and how far it is from the query.
struct SimilarityResult {
    int trackId = 0;
    double distance = 0.0;
};

/// Squared Euclidean distance between two equal-length feature vectors.
/// Cheaper than the true distance and monotonic, so it is enough for ranking.
double squaredEuclidean(const std::vector<double>& a, const std::vector<double>& b);

/// Euclidean distance between two equal-length feature vectors.
double euclidean(const std::vector<double>& a, const std::vector<double>& b);

/// Rank `candidates` against `query` by exact distance and return the K
/// closest, using a bounded max-heap (std::priority_queue) so we never fully
/// sort the candidate set.
///
/// @param tracks       collection of tracks.
/// @param trackIndex   optional prebuilt ID -> vector index map, avoiding O(N) per query.
/// @param candidateIds trackIds produced by SkipList::nearest.
/// @param k            number of results to return.
std::vector<SimilarityResult> topK(const std::vector<double>& query,
                                    const std::vector<Track>& tracks,
                                    const std::vector<int>& candidateIds,
                                    std::size_t k,
                                    const std::unordered_map<int, std::size_t>* trackIndex = nullptr);

}  // namespace ame
