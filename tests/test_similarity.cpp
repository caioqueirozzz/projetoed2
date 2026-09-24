// Unit tests for the similarity engine (plan §44, §49).
// Lightweight assert-based harness — no external framework required.

#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>

#include "similarity.hpp"

static void test_euclidean_basics() {
    std::vector<double> a{0.0, 0.0, 0.0};
    std::vector<double> b{3.0, 4.0, 0.0};
    assert(ame::squaredEuclidean(a, b) == 25.0);
    assert(std::abs(ame::euclidean(a, b) - 5.0) < 1e-9);
    assert(ame::euclidean(a, a) == 0.0);
}

// TODO: test_topk_returns_k_closest once topK() is implemented.

int main() {
    test_euclidean_basics();
    std::cout << "test_similarity: OK\n";
    return 0;
}
