#pragma once

#include <cstdint>
#include <vector>

namespace ame {

/// One node of the Skip List. `forward[i]` points to the next node on level i.
struct SkipNode {
    std::uint64_t key = 0;
    int trackId = 0;
    std::vector<SkipNode*> forward;

    SkipNode(std::uint64_t k, int id, int level)
        : key(k), trackId(id), forward(level + 1, nullptr) {}
};

/// Counters exposed for the benchmarks and the Structures Lab UI (plan §24, §29).
struct SkipListMetrics {
    std::uint64_t comparisons = 0;
    std::uint64_t insertions = 0;
    std::uint64_t removals = 0;
    std::uint64_t searches = 0;

    void reset() { *this = SkipListMetrics{}; }
};

/// Probabilistic ordered index keyed by AcousticKey (plan §10, §12).
///
/// Primary role: given a query key, return a window of the `numberOfCandidates`
/// closest tracks in key-space, which the similarity engine then re-ranks with
/// the exact Euclidean distance.
class SkipList {
public:
    explicit SkipList(int maxLevel = 16, double probability = 0.5);
    ~SkipList();

    SkipList(const SkipList&) = delete;
    SkipList& operator=(const SkipList&) = delete;

    void insert(std::uint64_t key, int trackId);
    bool remove(std::uint64_t key, int trackId);
    SkipNode* search(std::uint64_t key);

    /// Return up to `numberOfCandidates` trackIds whose keys are closest to
    /// `key`, gathered by walking outward from the search position.
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
};

}  // namespace ame
