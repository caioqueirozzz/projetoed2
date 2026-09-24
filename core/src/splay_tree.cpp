#include "splay_tree.hpp"

#include <algorithm>
#include <functional>
#include <string>

namespace ame {

// ── Destructor helper ─────────────────────────────────────────────────────────

namespace {
void destroy(SplayNode* node) {
    if (!node) return;
    destroy(node->left);
    destroy(node->right);
    delete node;
}

int subtreeHeight(const SplayNode* node) {
    if (!node) return -1;
    int l = subtreeHeight(node->left);
    int r = subtreeHeight(node->right);
    return 1 + (l > r ? l : r);
}
}  // namespace

SplayTree::~SplayTree() { destroy(root_); }

// ── Rotations ─────────────────────────────────────────────────────────────────
//
// Both rotations maintain parent pointers throughout. The root_ pointer is
// updated via the parent-of-x check (no grandparent → x was the root).

void SplayTree::rotateLeft(SplayNode* x) {
    SplayNode* y = x->right;        // y is the new local root after rotation

    // Move y's left subtree to x's right.
    x->right = y->left;
    if (y->left) y->left->parent = x;

    // Splice y into x's position in the tree.
    y->parent = x->parent;
    if      (!x->parent)           root_ = y;
    else if (x == x->parent->left) x->parent->left  = y;
    else                           x->parent->right = y;

    y->left   = x;
    x->parent = y;

    ++metrics_.rotations;
}

void SplayTree::rotateRight(SplayNode* x) {
    SplayNode* y = x->left;         // y is the new local root after rotation

    // Move y's right subtree to x's left.
    x->left = y->right;
    if (y->right) y->right->parent = x;

    // Splice y into x's position in the tree.
    y->parent = x->parent;
    if      (!x->parent)           root_ = y;
    else if (x == x->parent->left) x->parent->left  = y;
    else                           x->parent->right = y;

    y->right  = x;
    x->parent = y;

    ++metrics_.rotations;
}

// ── Splay ─────────────────────────────────────────────────────────────────────
//
// Bring `node` to the root using Zig / Zig-Zig / Zig-Zag steps (plan §19).
//
//  Zig:     node's parent IS the root (no grandparent) — one rotation.
//  Zig-Zig: node and parent lean the SAME way (left-left or right-right)
//           — rotate grandparent first, then parent (Sleator-Tarjan order).
//  Zig-Zag: node and parent lean DIFFERENT ways — rotate parent first,
//           then grandparent.
//
// lastStep_ records the last step type performed in this call (useful for
// the Structures Lab visualization). If the node is already the root the
// function returns immediately with SplayStep::None.

void SplayTree::splay(SplayNode* node) {
    if (!node->parent) {
        lastStep_ = SplayStep::None;
        return;
    }

    while (node->parent) {
        SplayNode* parent      = node->parent;
        SplayNode* grandparent = parent->parent;

        if (!grandparent) {
            // ── Zig ─────────────────────────────────────────────────────────
            lastStep_ = SplayStep::Zig;
            if (node == parent->left) rotateRight(parent);
            else                      rotateLeft(parent);

        } else if ((node == parent->left) == (parent == grandparent->left)) {
            // ── Zig-Zig (same direction) ─────────────────────────────────────
            lastStep_ = SplayStep::ZigZig;
            if (parent == grandparent->left) {
                rotateRight(grandparent);   // rotate at grandparent first
                rotateRight(parent);
            } else {
                rotateLeft(grandparent);
                rotateLeft(parent);
            }

        } else {
            // ── Zig-Zag (different directions) ───────────────────────────────
            lastStep_ = SplayStep::ZigZag;
            if (node == parent->right) {    // node is right child of left-child parent
                rotateLeft(parent);
                rotateRight(grandparent);
            } else {                        // node is left child of right-child parent
                rotateRight(parent);
                rotateLeft(grandparent);
            }
        }
    }
}

// ── Internal traversal helpers ────────────────────────────────────────────────

int SplayTree::depthOf(SplayNode* node) const {
    int depth = 0;
    while (node->parent) {
        ++depth;
        node = node->parent;
    }
    return depth;
}

// ── Public operations ─────────────────────────────────────────────────────────

void SplayTree::insert(int trackId) {
    SplayNode* cur    = root_;
    SplayNode* parent = nullptr;

    while (cur) {
        ++metrics_.comparisons;
        parent = cur;
        if      (trackId < cur->trackId) cur = cur->left;
        else if (trackId > cur->trackId) cur = cur->right;
        else {
            splay(cur);      // already present, just splay it
            return;
        }
    }

    auto* node = new SplayNode(trackId);
    if (!parent) {
        root_ = node;
        return;
    }
    node->parent = parent;
    if (trackId < parent->trackId) parent->left  = node;
    else                           parent->right = node;
    splay(node);
}

SplayNode* SplayTree::search(int trackId) {
    SplayNode* cur  = root_;
    SplayNode* last = nullptr;

    while (cur) {
        ++metrics_.comparisons;
        last = cur;
        if      (trackId < cur->trackId) cur = cur->left;
        else if (trackId > cur->trackId) cur = cur->right;
        else {
            splay(cur);
            return cur;     // cur == root_ after splay
        }
    }

    // Not found: splay the last visited node to maintain amortized bound.
    if (last) splay(last);
    return nullptr;
}

bool SplayTree::remove(int trackId) {
    // BST lookup without auto-splay side-effects.
    SplayNode* cur = root_;
    while (cur) {
        ++metrics_.comparisons;
        if      (trackId < cur->trackId) cur = cur->left;
        else if (trackId > cur->trackId) cur = cur->right;
        else break;
    }
    if (!cur) return false;

    // Splay target to root, then split.
    splay(cur);             // cur is now root_

    SplayNode* leftTree  = root_->left;
    SplayNode* rightTree = root_->right;
    if (leftTree)  leftTree->parent  = nullptr;
    if (rightTree) rightTree->parent = nullptr;

    delete root_;
    root_ = nullptr;

    if (!leftTree) {
        root_ = rightTree;
    } else if (!rightTree) {
        root_ = leftTree;
    } else {
        // Join: find the maximum of leftTree, splay it to leftTree's root,
        // then attach rightTree as its right child (max has no right child).
        root_ = leftTree;
        SplayNode* maxLeft = leftTree;
        while (maxLeft->right) maxLeft = maxLeft->right;
        splay(maxLeft);
        root_->right      = rightTree;
        rightTree->parent = root_;
    }

    return true;
}

void SplayTree::access(int trackId) {
    // Walk without splaying so we can record the pre-splay depth accurately.
    SplayNode* cur    = root_;
    SplayNode* parent = nullptr;

    while (cur) {
        ++metrics_.comparisons;
        parent = cur;
        if      (trackId < cur->trackId) cur = cur->left;
        else if (trackId > cur->trackId) cur = cur->right;
        else break;
    }

    SplayNode* target;
    if (cur) {
        target = cur;
        ++target->playCount;    // subsequent access to an existing track
    } else {
        // First time this track is accessed: insert it.
        // playCount starts at 1 (constructor) representing this first access.
        target = new SplayNode(trackId);
        if (!parent) {
            root_ = target;
            metrics_.lastDepthBefore = 0;
            metrics_.lastDepthAfter  = 0;
            return;
        }
        target->parent = parent;
        if (trackId < parent->trackId) parent->left  = target;
        else                           parent->right = target;
    }

    metrics_.lastDepthBefore = depthOf(target);
    splay(target);
    metrics_.lastDepthAfter = 0;    // always 0: target is now the root
}

// ── Info / display ────────────────────────────────────────────────────────────

int SplayTree::height() const {
    int h = subtreeHeight(root_);
    return h < 0 ? 0 : h;
}

std::string SplayTree::toAscii() const {
    if (!root_) return "(empty)\n";

    std::string out;
    out += "[" + std::to_string(root_->trackId) + "]\n";

    // Recursive builder: prints each child with its side label (L/R) so the
    // left/right relationship is always explicit even for single-child nodes.
    std::function<void(const SplayNode*, const std::string&, bool, bool)> build
        = [&](const SplayNode* node, const std::string& prefix, bool isLast, bool isLeft) {
        out += prefix;
        out += isLast ? "└── " : "├── ";
        out += (isLeft ? "L" : "R");
        out += ":" + std::to_string(node->trackId) + "\n";

        const std::string childPfx = prefix + (isLast ? "    " : "│   ");
        if (node->left && node->right) {
            build(node->left,  childPfx, false, true);
            build(node->right, childPfx, true,  false);
        } else if (node->left) {
            build(node->left,  childPfx, true, true);
        } else if (node->right) {
            build(node->right, childPfx, true, false);
        }
    };

    if (root_->left && root_->right) {
        build(root_->left,  "", false, true);
        build(root_->right, "", true,  false);
    } else if (root_->left) {
        build(root_->left,  "", true, true);
    } else if (root_->right) {
        build(root_->right, "", true, false);
    }

    return out;
}

}  // namespace ame
