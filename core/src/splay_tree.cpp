#include "splay_tree.hpp"
#include <algorithm>

namespace ame {
SplayTree::~SplayTree() {
    // Iterative destruction also supports a completely degenerate tree.
    while (root_) {
        if (root_->left) {
            auto* next = root_->left;
            root_->left = next->right;
            next->right = root_;
            root_ = next;
        } else {
            auto* next = root_->right;
            delete root_;
            root_ = next;
        }
    }
}
void SplayTree::refresh(SplayNode* n) {
    if (!n) return;
    n->subtreeSize = 1 + (n->left ? n->left->subtreeSize : 0) + (n->right ? n->right->subtreeSize : 0);
    n->subtreeHeight = 1 + std::max(n->left ? n->left->subtreeHeight : -1,
                                  n->right ? n->right->subtreeHeight : -1);
}
void SplayTree::refreshUp(SplayNode* n) { while (n) { refresh(n); n = n->parent; } }
void SplayTree::beginOperation() {
    steps_.clear(); lastStep_ = SplayStep::None;
    metrics_.lastDepthBefore = metrics_.lastDepthAfter = -1;
}
void SplayTree::rotateLeft(SplayNode* x) {
    auto* y = x->right;
    x->right = y->left;
    if (y->left) y->left->parent = x;
    y->parent = x->parent;
    if (!x->parent) root_ = y;
    else if (x == x->parent->left) x->parent->left = y;
    else x->parent->right = y;
    y->left = x; x->parent = y;
    refresh(x); refresh(y); ++metrics_.rotations;
}
void SplayTree::rotateRight(SplayNode* x) {
    auto* y = x->left;
    x->left = y->right;
    if (y->right) y->right->parent = x;
    y->parent = x->parent;
    if (!x->parent) root_ = y;
    else if (x == x->parent->left) x->parent->left = y;
    else x->parent->right = y;
    y->right = x; x->parent = y;
    refresh(x); refresh(y); ++metrics_.rotations;
}
void SplayTree::splay(SplayNode* n) {
    while (n->parent) {
        auto* p = n->parent;
        auto* g = p->parent;
        if (!g) {
            lastStep_ = SplayStep::Zig;
            if (n == p->left) rotateRight(p); else rotateLeft(p);
        } else if ((n == p->left) == (p == g->left)) {
            lastStep_ = SplayStep::ZigZig;
            if (p == g->left) { rotateRight(g); rotateRight(p); }
            else { rotateLeft(g); rotateLeft(p); }
        } else {
            lastStep_ = SplayStep::ZigZag;
            if (n == p->right) { rotateLeft(p); rotateRight(g); }
            else { rotateRight(p); rotateLeft(g); }
        }
        steps_.push_back(lastStep_);
    }
}
int SplayTree::depthOf(SplayNode* n) const {
    int d = 0; while (n->parent) { ++d; n = n->parent; } return d;
}
void SplayTree::insert(int id) {
    beginOperation();
    auto* n = root_; SplayNode* parent = nullptr;
    while (n) {
        ++metrics_.comparisons; parent = n;
        if (id == n->trackId) { metrics_.lastDepthBefore = depthOf(n); splay(n); metrics_.lastDepthAfter = 0; return; }
        n = id < n->trackId ? n->left : n->right;
    }
    auto* added = new SplayNode(id);
    added->parent = parent;
    if (!parent) root_ = added;
    else if (id < parent->trackId) parent->left = added;
    else parent->right = added;
    refreshUp(parent);
    metrics_.lastDepthBefore = depthOf(added);
    splay(added); metrics_.lastDepthAfter = 0;
}
SplayNode* SplayTree::search(int id) {
    beginOperation();
    auto* n = root_; SplayNode* last = nullptr;
    while (n) {
        ++metrics_.comparisons; last = n;
        if (id == n->trackId) { metrics_.lastDepthBefore = depthOf(n); splay(n); metrics_.lastDepthAfter = 0; return n; }
        n = id < n->trackId ? n->left : n->right;
    }
    if (last) splay(last);
    return nullptr;
}
bool SplayTree::remove(int id) {
    // A miss splays the last visited node too; repeated misses become cheap.
    if (!search(id)) return false;
    auto* left = root_->left; auto* right = root_->right;
    if (left) left->parent = nullptr;
    if (right) right->parent = nullptr;
    delete root_;
    root_ = left ? left : right;
    if (left && right) {
        auto* max = left;
        while (max->right) { ++metrics_.comparisons; max = max->right; }
        splay(max); root_->right = right; right->parent = root_; refresh(root_);
    }
    metrics_.lastDepthAfter = -1;
    return true;
}
void SplayTree::access(int id) {
    // One descent; insertion and counters are part of the access transaction.
    beginOperation();
    auto* n = root_; SplayNode* parent = nullptr;
    while (n) {
        ++metrics_.comparisons;
        if (id == n->trackId) break;
        parent = n; n = id < n->trackId ? n->left : n->right;
    }
    if (n) ++n->accessCount;
    else {
        n = new SplayNode(id); n->parent = parent;
        if (!parent) root_ = n;
        else if (id < parent->trackId) parent->left = n;
        else parent->right = n;
        refreshUp(parent);
    }
    metrics_.lastDepthBefore = depthOf(n); splay(n); metrics_.lastDepthAfter = 0;
}
int SplayTree::height() const { return root_ ? root_->subtreeHeight : 0; }
std::string SplayTree::toAscii(std::size_t maxNodes) const {
    if (!root_) return "(empty)\n";
    if (!maxNodes) return "... (truncated)\n";
    std::string out = "[" + std::to_string(root_->trackId) + "]\n";
    struct Pending { const SplayNode* n; std::string prefix; bool last, left; };
    std::vector<Pending> pending;
    auto children = [&](const SplayNode* n, const std::string& prefix) {
        if (n->right) pending.push_back({n->right, prefix, true, false});
        if (n->left) pending.push_back({n->left, prefix, !n->right, true});
    };
    children(root_, "");
    std::size_t shown = 1;
    while (!pending.empty() && shown < maxNodes) {
        auto item = std::move(pending.back()); pending.pop_back();
        out += item.prefix + (item.last ? "└── " : "├── ") + (item.left ? "L:" : "R:") + std::to_string(item.n->trackId) + "\n";
        ++shown;
        children(item.n, item.prefix + (item.last ? "    " : "│   "));
    }
    if (!pending.empty()) out += "... (truncated; " + std::to_string(size() - shown) + " nodes hidden)\n";
    return out;
}
} // namespace ame
