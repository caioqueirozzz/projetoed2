// Unit tests for the Skip List (plan §41, §49).
// Lightweight assert-based harness — no external framework required.

#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

#include "skip_list.hpp"

// ── helpers ───────────────────────────────────────────────────────────────────

static void check(bool cond, const char* msg) {
    if (!cond) {
        std::cerr << "FAIL: " << msg << "\n";
        std::exit(1);
    }
}

// ── tests ─────────────────────────────────────────────────────────────────────

static void test_empty() {
    ame::SkipList list;
    check(list.size() == 0, "empty list has size 0");
    check(list.search(42) == nullptr, "search on empty list returns nullptr");
    check(list.traverse().empty(), "traverse on empty list returns nothing");
    check(list.nearest(42, 10).empty(), "nearest on empty list returns nothing");
    check(list.levels().empty(), "levels on empty list returns nothing");
}

static void test_insert_and_search() {
    ame::SkipList list;
    list.insert(10, 1);
    list.insert(30, 3);
    list.insert(20, 2);

    check(list.size() == 3, "size after 3 inserts");
    check(list.search(10) != nullptr, "search finds 10");
    check(list.search(20) != nullptr, "search finds 20");
    check(list.search(30) != nullptr, "search finds 30");
    check(list.search(10)->trackId == 1, "search 10 returns id 1");
    check(list.search(20)->trackId == 2, "search 20 returns id 2");
    check(list.search(30)->trackId == 3, "search 30 returns id 3");
    check(list.search(99) == nullptr, "search for absent key returns nullptr");
}

static void test_sorted_order() {
    ame::SkipList list;
    // Insert out of order.
    list.insert(50, 5);
    list.insert(10, 1);
    list.insert(40, 4);
    list.insert(20, 2);
    list.insert(30, 3);

    const auto ids = list.traverse();
    check(ids.size() == 5, "traverse size");
    for (int i = 0; i < 5; ++i)
        check(ids[i] == i + 1, "traverse is sorted by key");
}

static void test_remove() {
    ame::SkipList list;
    list.insert(10, 1);
    list.insert(20, 2);
    list.insert(30, 3);

    check(list.remove(20, 2), "remove returns true for present node");
    check(list.size() == 2, "size after remove");
    check(list.search(20) == nullptr, "removed node not found by search");
    check(list.search(10) != nullptr, "neighbour 10 still present");
    check(list.search(30) != nullptr, "neighbour 30 still present");

    check(!list.remove(20, 2), "remove returns false for already-removed node");
    check(!list.remove(99, 9), "remove returns false for absent key");
}

static void test_remove_head_and_tail() {
    ame::SkipList list;
    list.insert(10, 1);
    list.insert(20, 2);
    list.insert(30, 3);

    check(list.remove(10, 1), "remove head key");
    check(list.search(10) == nullptr, "head key gone");
    check(list.search(20) != nullptr, "next key intact");

    check(list.remove(30, 3), "remove tail key");
    check(list.search(30) == nullptr, "tail key gone");
    check(list.size() == 1, "one key remaining");
}

static void test_duplicate_keys() {
    // Two tracks may share the same acoustic key; both must be stored and
    // each must be removable independently.
    ame::SkipList list;
    list.insert(42, 100);
    list.insert(42, 200);
    list.insert(42, 300);

    check(list.size() == 3, "all three duplicate-key nodes inserted");

    // search() returns the first with that key.
    auto* found = list.search(42);
    check(found != nullptr, "search finds a node with duplicate key");

    // Remove only the middle one.
    check(list.remove(42, 200), "remove middle duplicate");
    check(list.size() == 2, "size decremented by remove of duplicate");
    check(!list.remove(42, 200), "second remove of same (key,id) returns false");

    // The other two must survive.
    const auto ids = list.traverse();
    check(std::find(ids.begin(), ids.end(), 100) != ids.end(), "id 100 still present");
    check(std::find(ids.begin(), ids.end(), 300) != ids.end(), "id 300 still present");
    check(std::find(ids.begin(), ids.end(), 200) == ids.end(), "id 200 removed");
}

static void test_nearest_window() {
    // Insert keys 10,20,30,40,50 mapped to ids 1-5.
    ame::SkipList list;
    for (int i = 1; i <= 5; ++i)
        list.insert(i * 10, i);

    // Query key 25 (between 20 and 30); ask for 4 candidates.
    // Expected: ids for keys 10,20,30,40 (closest 2 on each side).
    const auto cands = list.nearest(25, 4);
    check(cands.size() == 4, "nearest returns 4 candidates");
    check(std::find(cands.begin(), cands.end(), 2) != cands.end(), "key 20 (id 2) in window");
    check(std::find(cands.begin(), cands.end(), 3) != cands.end(), "key 30 (id 3) in window");

    // Query key below all inserted keys: all candidates come from the right.
    const auto cands2 = list.nearest(1, 3);
    check((int)cands2.size() <= 3, "nearest respects budget");
    check(std::find(cands2.begin(), cands2.end(), 1) != cands2.end(), "id 1 (key 10) in right window");

    // Query key above all inserted keys: all candidates come from the left.
    const auto cands3 = list.nearest(999, 3);
    check(!cands3.empty(), "nearest above all keys returns left window");
    check(std::find(cands3.begin(), cands3.end(), 5) != cands3.end(), "id 5 (key 50) in left window");
}

static void test_nearest_respects_budget() {
    ame::SkipList list;
    for (int i = 0; i < 1000; ++i)
        list.insert(i, i);

    for (int budget : {50, 100, 250, 500}) {
        const auto cands = list.nearest(500, budget);
        check((int)cands.size() == budget, "nearest honours budget");
    }
}

static void test_levels_are_subsets() {
    // Every key on level k > 0 must also appear on level 0.
    ame::SkipList list;
    for (int i = 0; i < 200; ++i)
        list.insert(i * 7, i);

    const auto lvls = list.levels();
    check(!lvls.empty(), "levels() non-empty after inserts");

    // level 0 holds all keys; convert to set for O(1) lookup.
    const auto& base = lvls[0];
    check((int)base.size() == 200, "level 0 contains all inserted keys");

    for (std::size_t lvl = 1; lvl < lvls.size(); ++lvl) {
        for (std::uint64_t k : lvls[lvl]) {
            check(std::find(base.begin(), base.end(), k) != base.end(),
                  "higher-level key also present on level 0");
        }
    }
}

static void test_levels_are_sorted() {
    ame::SkipList list;
    for (int i = 99; i >= 0; --i)
        list.insert(i, i);

    for (const auto& lvl : list.levels()) {
        for (std::size_t i = 1; i < lvl.size(); ++i)
            check(lvl[i - 1] <= lvl[i], "keys within a level are non-decreasing");
    }
}

static void test_metrics() {
    ame::SkipList list;
    list.metrics().reset();

    list.insert(10, 1);
    list.insert(20, 2);
    check(list.metrics().insertions == 2, "insertion counter");

    list.search(10);
    check(list.metrics().searches == 1, "search counter");
    check(list.metrics().comparisons > 0, "comparisons counted during search");

    list.remove(10, 1);
    check(list.metrics().removals == 1, "removal counter");
}

// ── main ──────────────────────────────────────────────────────────────────────

int main() {
    test_empty();
    test_insert_and_search();
    test_sorted_order();
    test_remove();
    test_remove_head_and_tail();
    test_duplicate_keys();
    test_nearest_window();
    test_nearest_respects_budget();
    test_levels_are_subsets();
    test_levels_are_sorted();
    test_metrics();

    std::cout << "test_skiplist: all tests passed\n";
    return 0;
}
