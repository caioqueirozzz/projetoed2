#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace ame {

/// One laboratory node of the Splay Tree, keyed by integer ID.
struct SplayNode {
    int trackId = 0;
    int accessCount = 0;
    int subtreeSize = 1;
    int subtreeHeight = 0;

    SplayNode* left = nullptr;
    SplayNode* right = nullptr;
    SplayNode* parent = nullptr;

    explicit SplayNode(int id) : trackId(id), accessCount(1) {}
};

/// Type of the last splay step performed, for the laboratory visualization.
enum class SplayStep { None, Zig, ZigZig, ZigZag };

/// Metrics collected per operation, surfaced in Structures Lab.
struct SplayMetrics {
    std::uint64_t comparisons = 0;
    std::uint64_t rotations = 0;
    int lastDepthBefore = -1;
    int lastDepthAfter = -1;

    void reset() { *this = SplayMetrics{}; }
};

/// Self-adjusting BST for laboratory experiments and access benchmarks.
/// Every access splays the touched node to the root, exploiting temporal
/// locality so recently accessed nodes stay shallow.
class SplayTree {
public:
    SplayTree() = default;
    ~SplayTree();

    SplayTree(const SplayTree&) = delete;
    SplayTree& operator=(const SplayTree&) = delete;

    void insert(int trackId);
    SplayNode* search(int trackId);
    bool remove(int trackId);

    /// Find (or insert) the node, increment its access count, and splay it.
    void access(int trackId);

    SplayNode* getRoot() const { return root_; }
    int height() const;

    /// Pretty-printed tree snapshot for the laboratory before/after views.
    std::string toAscii(std::size_t maxNodes = 40) const;
    int size() const { return root_ ? root_->subtreeSize : 0; }
    const std::vector<SplayStep>& steps() const { return steps_; }

    SplayStep lastStep() const { return lastStep_; }
    const SplayMetrics& metrics() const { return metrics_; }
    SplayMetrics& metrics() { return metrics_; }

private:
    void rotateLeft(SplayNode* node);
    void rotateRight(SplayNode* node);
    void splay(SplayNode* node);
    int depthOf(SplayNode* node) const;
    void beginOperation();
    static void refresh(SplayNode* node);
    static void refreshUp(SplayNode* node);

    SplayNode* root_ = nullptr;
    SplayStep lastStep_ = SplayStep::None;
    SplayMetrics metrics_;
    std::vector<SplayStep> steps_;
};

}  // namespace ame
