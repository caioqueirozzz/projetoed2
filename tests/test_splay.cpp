// Unit tests for the Splay Tree.
// Lightweight assert-based harness — no external framework required.
//
// For Zig / Zig-Zig / Zig-Zag tests the tree state is set up by tracing the
// insert/access sequences manually (comments show each intermediate state).

#include <algorithm>
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

#include "splay_tree.hpp"

// ── helpers ───────────────────────────────────────────────────────────────────

static void check(bool cond, const char* msg) {
    if (!cond) {
        std::cerr << "FAIL: " << msg << "\n";
        std::exit(1);
    }
}

// In-order traversal → sorted list of trackIds (verifies BST property).
static std::vector<int> inorder(const ame::SplayNode* node) {
    if (!node) return {};
    auto left  = inorder(node->left);
    auto right = inorder(node->right);
    left.push_back(node->trackId);
    left.insert(left.end(), right.begin(), right.end());
    return left;
}

static std::vector<int> inorder(const ame::SplayTree& tree) {
    return inorder(tree.getRoot());
}

// ── tests ─────────────────────────────────────────────────────────────────────

static void test_empty() {
    ame::SplayTree tree;
    check(tree.getRoot() == nullptr, "empty tree has null root");
    check(tree.search(99) == nullptr, "search on empty tree returns nullptr");
    check(tree.height() == 0, "empty tree height is 0");
    check(tree.toAscii() == "(empty)\n", "toAscii on empty tree");
}

static void test_insert_and_search() {
    ame::SplayTree tree;
    tree.insert(20);
    tree.insert(10);
    tree.insert(30);

    check(tree.search(20) != nullptr, "search finds 20");
    check(tree.search(10) != nullptr, "search finds 10");
    check(tree.search(30) != nullptr, "search finds 30");
    check(tree.search(99) == nullptr, "search misses absent key");

    // Each successful search splays the found node to root.
    tree.search(20);
    check(tree.getRoot()->trackId == 20, "search splays found node to root");
}

static void test_access_splays_to_root() {
    ame::SplayTree tree;
    tree.insert(20);
    tree.insert(10);
    tree.insert(30);

    tree.access(10);
    check(tree.getRoot()->trackId == 10, "access(10) brings 10 to root");

    tree.access(30);
    check(tree.getRoot()->trackId == 30, "access(30) brings 30 to root");

    tree.access(20);
    check(tree.getRoot()->trackId == 20, "access(20) brings 20 to root");
}

// ── Zig ───────────────────────────────────────────────────────────────────────
//
// Setup via: insert(20), insert(10)
//   insert(20): root=20
//   insert(10): 10 < 20, left of 20; splay(10): parent=20 (root), Zig.
//               rotateRight(20) → root=10, 10->right=20
//
// Now access(20): 20 is right child of root(10) → depth=1 → Zig.
static void test_zig() {
    ame::SplayTree tree;
    tree.insert(20);
    tree.insert(10);
    // State: root=10, right=20

    tree.access(20);

    check(tree.lastStep() == ame::SplayStep::Zig, "Zig step detected");
    check(tree.getRoot()->trackId == 20, "Zig brings 20 to root");
    check(tree.getRoot()->left  != nullptr &&
          tree.getRoot()->left->trackId == 10, "10 is left of 20 after Zig");
}

// ── Zig-Zig ───────────────────────────────────────────────────────────────────
//
// Insert 1,2,3,4 in order. Each insert splays the new node via a Zig, creating
// a left-leaning chain rooted at the largest inserted key:
//   insert(1): root=1
//   insert(2): right of 1, Zig rotateLeft(1)  → root=2, left=1
//   insert(3): right of 2, Zig rotateLeft(2)  → root=3, left=2, 2->left=1
//   insert(4): right of 3, Zig rotateLeft(3)  → root=4, left=3, 3->left=2, 2->left=1
//
// access(2): 2 is left child of 3, 3 is left child of 4 → same direction → Zig-Zig.
//   rotateRight(4): root=3, right=4
//   rotateRight(3): root=2, right=3, 3->right=4
static void test_zig_zig() {
    ame::SplayTree tree;
    tree.insert(1);
    tree.insert(2);
    tree.insert(3);
    tree.insert(4);
    // State: root=4, 4->left=3, 3->left=2, 2->left=1

    tree.access(2);

    check(tree.lastStep() == ame::SplayStep::ZigZig, "Zig-Zig step detected");
    check(tree.getRoot()->trackId == 2, "Zig-Zig brings 2 to root");

    // BST property must hold after the rotations.
    const auto ids = inorder(tree);
    check(ids == (std::vector<int>{1, 2, 3, 4}), "Zig-Zig preserves BST order");
}

// ── Zig-Zag ───────────────────────────────────────────────────────────────────
//
// Build the shape: root=3, 3->left=1, 1->right=2  (node 2 is right of left child)
//
//   insert(3):  root=3
//   access(1):  not found; insert left of 3; splay(1): Zig rotateRight(3)
//               → root=1, right=3
//   access(3):  right child of root(1) → Zig rotateLeft(1)
//               → root=3, left=1
//   access(2):  not found; 2<3 → left, 2>1 → right; insert as 1->right.
//               State: root=3, left=1, 1->right=2
//               2 is RIGHT child of LEFT child → Zig-Zag!
//                 rotateLeft(1): 2 takes 1's spot under 3 → 3->left=2, 2->left=1
//                 rotateRight(3): 2 becomes root → root=2, left=1, right=3
static void test_zig_zag() {
    ame::SplayTree tree;
    tree.insert(3);
    tree.access(1);   // creates 1, Zig
    tree.access(3);   // 3 is right of root(1), Zig
    tree.access(2);   // creates 2 as right child of left child → Zig-Zag

    check(tree.lastStep() == ame::SplayStep::ZigZag, "Zig-Zag step detected");
    check(tree.getRoot()->trackId == 2, "Zig-Zag brings 2 to root");
    check(tree.getRoot()->left  != nullptr &&
          tree.getRoot()->left->trackId  == 1, "1 is left of 2 after Zig-Zag");
    check(tree.getRoot()->right != nullptr &&
          tree.getRoot()->right->trackId == 3, "3 is right of 2 after Zig-Zag");

    // BST order preserved.
    const auto ids = inorder(tree);
    check(ids == (std::vector<int>{1, 2, 3}), "Zig-Zag preserves BST order");
}

static void test_remove() {
    ame::SplayTree tree;
    tree.insert(10);
    tree.insert(20);
    tree.insert(30);

    check(tree.remove(20), "remove returns true for present id");
    check(tree.search(20) == nullptr, "removed id not found");
    check(tree.search(10) != nullptr, "sibling 10 still present");
    check(tree.search(30) != nullptr, "sibling 30 still present");

    // BST property must hold after remove.
    const auto ids = inorder(tree);
    check(std::find(ids.begin(), ids.end(), 20) == ids.end(), "20 absent from inorder");
    check(std::find(ids.begin(), ids.end(), 10) != ids.end(), "10 present in inorder");
    check(std::find(ids.begin(), ids.end(), 30) != ids.end(), "30 present in inorder");

    check(!tree.remove(20),  "remove returns false for already-removed id");
    check(!tree.remove(999), "remove returns false for absent id");

    // Remove remaining nodes to empty the tree.
    check(tree.remove(10), "remove 10");
    check(tree.remove(30), "remove 30");
    check(tree.getRoot() == nullptr, "tree is empty after removing all nodes");
}

static void test_remove_root() {
    ame::SplayTree tree;
    tree.insert(5);
    tree.remove(5);
    check(tree.getRoot() == nullptr, "removing the only node empties the tree");
}

static void test_play_count() {
    ame::SplayTree tree;

    // First access creates the node; constructor sets accessCount=1 (first access).
    tree.access(7);
    check(tree.getRoot()->trackId == 7, "7 at root after first access");
    check(tree.getRoot()->accessCount == 1, "accessCount is 1 after first access");

    // Each subsequent access increments accessCount.
    tree.access(7);
    check(tree.getRoot()->accessCount == 2, "accessCount increments to 2");
    tree.access(7);
    check(tree.getRoot()->accessCount == 3, "accessCount increments to 3");

    // Access to a different node must not change 7's accessCount.
    tree.access(99);
    tree.access(7);
    check(tree.getRoot()->accessCount == 4, "accessCount continues incrementing");
}

static void test_depth_metrics() {
    ame::SplayTree tree;
    // Build left chain of depth 3: root=4, 4->left=3, 3->left=2, 2->left=1
    tree.insert(1);
    tree.insert(2);
    tree.insert(3);
    tree.insert(4);
    // 1 is at depth 3 from root 4.

    tree.access(1);

    check(tree.metrics().lastDepthBefore == 3, "depth before splay recorded as 3");
    check(tree.metrics().lastDepthAfter  == 0, "depth after splay is 0 (root)");
    check(tree.getRoot()->trackId == 1,        "1 is now at root");
}

static void test_locality_keeps_hot_shallow() {
    // Repeatedly accessing the same track should keep it at the root (depth 0).
    ame::SplayTree tree;
    for (int i = 1; i <= 20; ++i)
        tree.insert(i);

    for (int rep = 0; rep < 10; ++rep) {
        tree.access(5);
        check(tree.getRoot()->trackId == 5, "hot track 5 stays at root");
        check(tree.metrics().lastDepthAfter == 0, "depth after access is always 0");
    }
}

static void test_bst_property_after_many_accesses() {
    ame::SplayTree tree;
    for (int i : {15, 5, 25, 3, 10, 20, 30})
        tree.insert(i);

    const std::vector<int> sorted = {3, 5, 10, 15, 20, 25, 30};
    check(inorder(tree) == sorted, "BST order correct after initial inserts");

    // Random accesses should never break BST invariant.
    for (int id : {10, 5, 30, 15, 3}) {
        tree.access(id);
        check(inorder(tree) == sorted, "BST order preserved after access");
    }
}

static void test_height() {
    ame::SplayTree tree;
    check(tree.height() == 0, "empty tree height is 0");

    tree.insert(10);
    check(tree.height() == 0, "single-node tree height is 0");

    tree.insert(5);
    check(tree.height() == 1, "two-node tree height is 1");

    tree.insert(15);
    // After insert(15): 15 is right of 10; Zig rotateLeft(10).
    // root=15, left=10, 10->left=5. height=2.
    check(tree.height() == 2, "three-node left chain height is 2");
}

static void test_ascii_non_empty() {
    ame::SplayTree tree;
    tree.insert(20);
    tree.insert(10);
    tree.insert(30);

    const std::string ascii = tree.toAscii();
    check(!ascii.empty(), "toAscii is non-empty");

    // Root id must appear in the output.
    const int rootId = tree.getRoot()->trackId;
    const std::string rootStr = "[" + std::to_string(rootId) + "]";
    check(ascii.find(rootStr) != std::string::npos, "root id appears in toAscii");
}

static void test_rotations_counted() {
    ame::SplayTree tree;
    tree.metrics().reset();

    // Insert 1,2,3,4 in order — each insert triggers at least one Zig rotation.
    tree.insert(1);
    tree.insert(2);
    tree.insert(3);
    tree.insert(4);
    check(tree.metrics().rotations > 0, "rotations counted during splay");

    const auto rotBefore = tree.metrics().rotations;
    tree.access(1);  // depth=3 → Zig-Zig (2 rotations) + Zig (1 rotation)
    check(tree.metrics().rotations > rotBefore, "additional rotations counted on access");
}

// ── main ──────────────────────────────────────────────────────────────────────

int main() {
    test_empty();
    test_insert_and_search();
    test_access_splays_to_root();
    test_zig();
    test_zig_zig();
    test_zig_zag();
    test_remove();
    test_remove_root();
    test_play_count();
    test_depth_metrics();
    test_locality_keeps_hot_shallow();
    test_bst_property_after_many_accesses();
    test_height();
    test_ascii_non_empty();
    test_rotations_counted();

    std::cout << "test_splay: all tests passed\n";
    return 0;
}
