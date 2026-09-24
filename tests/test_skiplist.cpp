// Unit tests for the Skip List (plan §41, §49).
// Lightweight assert-based harness — no external framework required.

#include <cassert>
#include <iostream>

#include "skip_list.hpp"

static void test_starts_empty() {
    ame::SkipList list;
    assert(list.size() == 0);
    // TODO: enable once insert() is implemented.
    // list.insert(42, 1);
    // assert(list.size() == 1);
    // assert(list.search(42) != nullptr);
}

// TODO: test_insert_search, test_remove, test_nearest_window, test_ordering.

int main() {
    test_starts_empty();
    std::cout << "test_skiplist: OK (scaffold)\n";
    return 0;
}
