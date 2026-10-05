#include "acoustic_search.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <queue>
#include <stdexcept>

namespace ame {
using Clock = std::chrono::steady_clock;
static double ms(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}
std::uint64_t AcousticSearch::radialKey(double distance) {
    return static_cast<std::uint64_t>(std::floor(distance * 1e8));
}
AcousticSearch::AcousticSearch(std::vector<Track> tracks, unsigned seed)
    : tracks_(std::move(tracks)), morton_(16, .5, seed), radial_(16, .5, seed) {
    if (tracks_.empty()) throw std::invalid_argument("Empty dataset");
    const auto dims = tracks_[0].features.size();
    if (!dims) throw std::invalid_argument("Empty features");
    for (std::size_t i = 0; i < tracks_.size(); ++i) {
        if (!ids_.emplace(tracks_[i].id, i).second) throw std::invalid_argument("Duplicate track ID");
        if (tracks_[i].features.size() != dims) throw std::invalid_argument("Inconsistent feature dimensions");
        for (double v : tracks_[i].features)
            if (!std::isfinite(v) || v < 0 || v > 1) throw std::invalid_argument("Features must be finite and normalized");
        morton_.insert(tracks_[i].acousticKey, tracks_[i].id);
    }
    seen_.resize(tracks_.size(), 0);
    pivotDistances_.resize(tracks_.size());
    std::vector<double> nearestPivot(tracks_.size(), std::numeric_limits<double>::infinity());
    std::size_t pivot = 0;
    for (std::size_t p = 0; p < std::min<std::size_t>(4, tracks_.size()); ++p) {
        for (std::size_t i = 0; i < tracks_.size(); ++i) {
            const double d = euclidean(tracks_[pivot].features, tracks_[i].features);
            pivotDistances_[i].push_back(d);
            nearestPivot[i] = std::min(nearestPivot[i], d);
        }
        pivot = std::max_element(nearestPivot.begin(), nearestPivot.end()) - nearestPivot.begin();
    }
    for (std::size_t i = 0; i < tracks_.size(); ++i)
        radial_.insert(radialKey(pivotDistances_[i][0]), tracks_[i].id);
}
const Track& AcousticSearch::track(int id) const {
    auto it = ids_.find(id);
    if (it == ids_.end()) throw std::invalid_argument("Unknown track ID");
    return tracks_[it->second];
}
SearchReport AcousticSearch::search(int queryId, int budget, int k, bool exact, bool evaluate) {
    const auto& q = track(queryId);
    if (budget <= 0 || k <= 0) throw std::invalid_argument("Candidate count and top_k must be positive");
    const auto qi = ids_.at(queryId);
    SearchReport r; r.exact = exact;
    auto start = Clock::now();
    const auto comps = morton_.metrics().comparisons + radial_.metrics().comparisons;
    auto indexStart = Clock::now();
    const auto seedBudget = std::min<std::size_t>(budget, tracks_.size() - 1);
    auto seeds = morton_.nearest(q.acousticKey, static_cast<int>(seedBudget + 1));
    seeds.erase(std::remove(seeds.begin(), seeds.end(), queryId), seeds.end());
    if (seeds.size() > seedBudget) seeds.resize(seedBudget);
    r.initialCandidates = seeds.size();
    r.indexMs = ms(indexStart);
    using Entry = std::pair<double, int>;
    std::priority_queue<Entry> heap;
    const auto limit = std::min<std::size_t>(k, tracks_.size() - 1);
    if (++epoch_ == 0) { std::fill(seen_.begin(), seen_.end(), 0); epoch_ = 1; }
    seen_[qi] = epoch_;
    auto score = [&](std::size_t i) {
        if (seen_[i] == epoch_ || !limit) return;
        seen_[i] = epoch_; ++r.candidates;
        Entry entry{squaredEuclidean(q.features, tracks_[i].features), tracks_[i].id};
        if (heap.size() < limit) heap.push(entry);
        else if (entry < heap.top()) { heap.pop(); heap.push(entry); }
    };
    for (int id : seeds) score(ids_.at(id));
    if (exact && limit) {
        indexStart = Clock::now();
        const auto key = radialKey(pivotDistances_[qi][0]);
        auto [left, right] = radial_.neighbors(key);
        r.indexMs += ms(indexStart);
        auto bound = [&](const SkipNode* n) {
            if (!n) return std::numeric_limits<double>::infinity();
            auto delta = n->key > key ? n->key - key : key - n->key;
            // Subtract one quantization bin: conservative even at boundaries.
            return delta > 1 ? static_cast<double>(delta - 1) / 1e8 : 0.0;
        };
        while (left || right) {
            const double lb = bound(left), rb = bound(right);
            const double radius = heap.size() == limit ? std::sqrt(heap.top().first) : std::numeric_limits<double>::infinity();
            if (std::min(lb, rb) > radius + 1e-12) break;
            const SkipNode* node;
            if (lb <= rb) { node = left; left = left->backward; }
            else { node = right; right = right->forward[0]; }
            ++r.visited;
            const auto i = ids_.at(node->trackId);
            if (seen_[i] == epoch_) continue;
            bool skip = false;
            for (std::size_t p = 0; p < pivotDistances_[qi].size(); ++p)
                if (std::abs(pivotDistances_[i][p] - pivotDistances_[qi][p]) > radius + 1e-12) { skip = true; break; }
            if (!skip) score(i);
        }
        r.pruned = tracks_.size() - 1 - r.candidates;
    }
    while (!heap.empty()) { r.results.push_back({heap.top().second, std::sqrt(heap.top().first)}); heap.pop(); }
    std::reverse(r.results.begin(), r.results.end());
    r.comparisons = morton_.metrics().comparisons + radial_.metrics().comparisons - comps;
    r.totalMs = ms(start); r.similarityMs = std::max(0.0, r.totalMs - r.indexMs);
    if (evaluate) {
        std::vector<int> all;
        for (const auto& t : tracks_) if (t.id != queryId) all.push_back(t.id);
        auto bruteStart = Clock::now();
        const auto truth = topK(q.features, tracks_, all, k, &ids_);
        r.bruteMs = ms(bruteStart);
        int hits = 0;
        for (const auto& result : r.results)
            hits += std::any_of(truth.begin(), truth.end(), [&](const auto& t) { return t.trackId == result.trackId; });
        r.recall = truth.empty() ? 1.0 : static_cast<double>(hits) / truth.size();
    }
    return r;
}
}
