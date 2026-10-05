#pragma once

#include <cstdint>
#include <vector>
#include <random>
#include <utility>

namespace ame {

/// One node of the Skip List. `forward[i]` points to the next node on level i.
struct SkipNode {
    std::uint64_t key = 0;
    int trackId = 0;
    std::vector<SkipNode*> forward;
    SkipNode* backward = nullptr;  // previous node at level 0, excluding sentinel

    SkipNode(std::uint64_t k, int id, int level)
        : key(k), trackId(id), forward(level + 1, nullptr) {}
};

/// Counters exposed for the benchmarks and the Structures Lab UI.
struct SkipListMetrics {
    std::uint64_t comparisons = 0;
    std::uint64_t insertions = 0;
    std::uint64_t removals = 0;
    std::uint64_t searches = 0;

    void reset() { *this = SkipListMetrics{}; }
};

/// Probabilistic ordered index keyed by AcousticKey.
///
/// Primary role: given a query key, return a window of the `numberOfCandidates`
/// closest tracks in key-space, which the similarity engine then re-ranks with
/// the exact Euclidean distance.
class SkipList {
public:
    explicit SkipList(int maxLevel = 16, double probability = 0.5, unsigned seed = 42);
    ~SkipList();

    SkipList(const SkipList&) = delete;
    SkipList& operator=(const SkipList&) = delete;

    void insert(std::uint64_t key, int trackId);
    bool remove(std::uint64_t key, int trackId);
    SkipNode* search(std::uint64_t key);
    bool contains(std::uint64_t key, int trackId);
    bool update(std::uint64_t oldKey, int trackId, std::uint64_t newKey);
    std::pair<const SkipNode*, const SkipNode*> neighbors(std::uint64_t key);
    std::vector<std::vector<std::pair<std::uint64_t, int>>> snapshot(std::size_t limit = 80) const;
    std::size_t memoryBytes() const;
    const std::vector<std::pair<int, int>>& lastPath() const { return lastPath_; }

    /// Return an ordered window around `key` in expected O(log N + C).
    /// Fill from the other side when a boundary is reached (C = budget).
    std::vector<int> nearest(std::uint64_t key, int numberOfCandidates);

    /// In-order traversal of all trackIds (level-1 chain).
    std::vector<int> traverse() const;

    /// Snapshot of the keys present at each level, for visualization.
    std::vector<std::vector<std::uint64_t>> levels() const;

    int size() const { return size_; }
    const SkipListMetrics& metrics() const { return metrics_; }
    SkipListMetrics& metrics() { return metrics_; }

private:
    int randomLevel();

    int maxLevel_;
    double probability_;
    int currentLevel_ = 0;
    int size_ = 0;
    SkipNode* head_;
    SkipListMetrics metrics_;
    std::mt19937 rng_;
    std::vector<std::pair<int, int>> lastPath_; // (level, visited track ID)
};

}  // namespace ame
