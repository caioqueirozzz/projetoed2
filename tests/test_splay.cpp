// Unit tests for the Splay Tree (plan §42, §49).
// Lightweight assert-based harness — no external framework required.

#include <cassert>
#include <iostream>

#include "splay_tree.hpp"

static void test_starts_empty() {
    ame::SplayTree tree;
    assert(tree.getRoot() == nullptr);
    // TODO: enable once access()/insert() are implemented.
    // tree.access(7);
    // assert(tree.getRoot() != nullptr);
    // assert(tree.getRoot()->trackId == 7);  // accessed node splays to root
}

// TODO: test_zig, test_zig_zig, test_zig_zag, test_locality_keeps_hot_shallow.

int main() {
    test_starts_empty();
    std::cout << "test_splay: OK (scaffold)\n";
    return 0;
}
