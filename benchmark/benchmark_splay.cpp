// Benchmark: Splay Tree vs BST vs AVL/std::map (plan §33-§35).
// Two access scenarios:
//   A — uniform distribution      -> benchmark_splay_uniform.csv
//   B — locality (80/20 access)   -> benchmark_splay_locality.csv

#include <iostream>

#include "splay_tree.hpp"

int main() {
    // TODO: run both access scenarios, measuring comparisons, average depth,
    //       depth of the hottest tracks, rotations, time, and amortized cost.
    std::cout << "benchmark_splay: scaffold — not yet implemented\n";
    return 0;
}
