#include "similarity.hpp"

#include <cmath>

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

std::vector<SimilarityResult> topK(const std::vector<double>& /*query*/,
                                   const std::vector<Track>& /*tracks*/,
                                   const std::vector<int>& /*candidateIds*/,
                                   std::size_t /*k*/) {
    // TODO: score each candidate against `query` with squaredEuclidean and keep
    //       the K smallest via a bounded max-heap (std::priority_queue).
    return {};
}

}  // namespace ame
