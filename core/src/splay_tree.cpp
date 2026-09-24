#include "splay_tree.hpp"

namespace ame {

namespace {
void destroy(SplayNode* node) {
    if (node == nullptr) return;
    destroy(node->left);
    destroy(node->right);
    delete node;
}
}  // namespace

SplayTree::~SplayTree() { destroy(root_); }

void SplayTree::rotateLeft(SplayNode* /*node*/) {
    // TODO: left rotation; increment metrics_.rotations.
}

void SplayTree::rotateRight(SplayNode* /*node*/) {
    // TODO: right rotation; increment metrics_.rotations.
}

void SplayTree::splay(SplayNode* /*node*/) {
    // TODO: bring `node` to the root via Zig / Zig-Zig / Zig-Zag steps and
    //       record the last performed step in lastStep_.
}

int SplayTree::depthOf(SplayNode* /*node*/) const {
    // TODO: distance from `node` to the root.
    return -1;
}

void SplayTree::insert(int /*trackId*/) {
    // TODO: BST insert then splay the new node to the root.
}

SplayNode* SplayTree::search(int /*trackId*/) {
    // TODO: BST search, splaying the found (or last-visited) node.
    return nullptr;
}

bool SplayTree::remove(int /*trackId*/) {
    // TODO: splay target to root, then join left/right subtrees.
    return false;
}

void SplayTree::access(int /*trackId*/) {
    // TODO: record depth before, find-or-insert + bump playCount, splay,
    //       record depth after (metrics_.lastDepthBefore/After).
}

int SplayTree::height() const {
    // TODO: height of the tree rooted at root_.
    return 0;
}

std::string SplayTree::toAscii() const {
    // TODO: render the tree for the before/after visualization (plan §27).
    return {};
}

}  // namespace ame
