#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace ame {

/// One node of the Splay Tree, keyed by trackId (plan §18).
struct SplayNode {
    int trackId = 0;
    int playCount = 0;

    SplayNode* left = nullptr;
    SplayNode* right = nullptr;
    SplayNode* parent = nullptr;

    explicit SplayNode(int id) : trackId(id), playCount(1) {}
};

/// Type of the last splay step performed, for the visualization (plan §19, §27).
enum class SplayStep { None, Zig, ZigZig, ZigZag };

/// Metrics collected per access, surfaced in the Playback Profile page (§26).
struct SplayMetrics {
    std::uint64_t comparisons = 0;
    std::uint64_t rotations = 0;
    int lastDepthBefore = -1;
    int lastDepthAfter = -1;

    void reset() { *this = SplayMetrics{}; }
};

/// Self-adjusting BST modelling the user's recent playback pattern (plan §17).
/// Every access splays the touched track to the root, exploiting temporal
/// locality so recently played tracks stay shallow.
class SplayTree {
public:
    SplayTree() = default;
    ~SplayTree();

    SplayTree(const SplayTree&) = delete;
    SplayTree& operator=(const SplayTree&) = delete;

    void insert(int trackId);
    SplayNode* search(int trackId);
    bool remove(int trackId);

    /// Register a playback/selection: find (or insert) the track, bump its
    /// playCount, and splay it to the root.
    void access(int trackId);

    SplayNode* getRoot() const { return root_; }
    int height() const;

    /// Pretty-printed tree snapshot (for the before/after views in §27).
    std::string toAscii() const;

    SplayStep lastStep() const { return lastStep_; }
    const SplayMetrics& metrics() const { return metrics_; }
    SplayMetrics& metrics() { return metrics_; }

private:
    void rotateLeft(SplayNode* node);
    void rotateRight(SplayNode* node);
    void splay(SplayNode* node);
    int depthOf(SplayNode* node) const;

    SplayNode* root_ = nullptr;
    SplayStep lastStep_ = SplayStep::None;
    SplayMetrics metrics_;
};

}  // namespace ame
