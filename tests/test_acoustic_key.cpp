// Unit tests for the Acoustic Key (plan §43).
// All expected values are derived analytically and annotated inline.

#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <vector>

#include "acoustic_key.hpp"

// ── helpers ───────────────────────────────────────────────────────────────────

static void check(bool cond, const char* msg) {
    if (!cond) {
        std::cerr << "FAIL: " << msg << "\n";
        std::exit(1);
    }
}

// Maximum possible key for given (dimensions, bitsPerDim): all bits set.
static std::uint64_t maxKey(int dimensions, int bitsPerDim) {
    return (1ULL << (dimensions * bitsPerDim)) - 1ULL;
}

// ── basic properties ──────────────────────────────────────────────────────────

static void test_same_features_same_key() {
    ame::AcousticKey k(4, 8);
    const std::vector<double> feat{0.2, 0.5, 0.8, 0.1};
    check(k.encode(feat) == k.encode(feat), "same features → same key (deterministic)");
}

static void test_zero_features_give_key_zero() {
    // All-zero normalized features quantize to 0 on every dimension.
    // Interleaving all-zero coords yields 0.
    ame::AcousticKey k(6, 10);
    const std::vector<double> zeros(6, 0.0);
    check(k.encode(zeros) == 0, "all-zero features → key 0");
}

static void test_max_features_give_max_key() {
    // All-1.0 normalized features quantize to maxVal on every dimension.
    // Interleaving all-max coords sets every output bit → maxKey.
    //
    // dims=3, bits=3: maxVal=7=0b111, maxKey=(1<<9)-1=511.
    // interleave([7,7,7]) with dims=3, bits=3:
    //   bit 0 of each coord at positions 0,1,2 → bits 0-2 all set
    //   bit 1 of each coord at positions 3,4,5 → bits 3-5 all set
    //   bit 2 of each coord at positions 6,7,8 → bits 6-8 all set
    //   result = 0b111111111 = 511 = (1<<9)-1 ✓
    ame::AcousticKey k(3, 3);
    const std::vector<double> ones(3, 1.0);
    check(k.encode(ones) == maxKey(3, 3), "all-1.0 features → max key");
}

static void test_clamping_below_zero() {
    ame::AcousticKey k(2, 4);
    const std::vector<double> zeros{0.0, 0.0};
    const std::vector<double> negatives{-0.5, -100.0};
    check(k.encode(negatives) == k.encode(zeros),
          "values below 0 clamp to 0.0 (same key as zero vector)");
}

static void test_clamping_above_one() {
    ame::AcousticKey k(2, 4);
    const std::vector<double> ones{1.0, 1.0};
    const std::vector<double> overflow{1.5, 99.0};
    check(k.encode(overflow) == k.encode(ones),
          "values above 1 clamp to 1.0 (same key as max vector)");
}

static void test_short_feature_vector_padded_with_zeros() {
    // Missing dimensions default to 0.0.
    ame::AcousticKey k(4, 4);
    const std::vector<double> full{0.5, 0.5, 0.0, 0.0};
    const std::vector<double> short_v{0.5, 0.5};       // 2 entries instead of 4
    check(k.encode(short_v) == k.encode(full),
          "short feature vector padded with 0 matches explicit zeros");
}

// ── known interleave values ───────────────────────────────────────────────────
//
// dims=2, bits=2, maxVal=3.
// Bit layout: output bit at position b*2+d is the b-th bit of coords[d].
//
//   encode([1.0, 0.0]):
//     quantize(1.0) = 3 = 0b11,  quantize(0.0) = 0 = 0b00
//     interleave([3, 0]):
//       b=0 d=0: bit0(3)=1 → pos 0
//       b=0 d=1: bit0(0)=0 → pos 1
//       b=1 d=0: bit1(3)=1 → pos 2
//       b=1 d=1: bit1(0)=0 → pos 3
//     result = (1<<0)|(1<<2) = 1|4 = 5
//
//   encode([0.0, 1.0]):
//     quantize(0.0)=0, quantize(1.0)=3
//     interleave([0, 3]):
//       b=0 d=0: bit0(0)=0 → pos 0
//       b=0 d=1: bit0(3)=1 → pos 1
//       b=1 d=0: bit1(0)=0 → pos 2
//       b=1 d=1: bit1(3)=1 → pos 3
//     result = (1<<1)|(1<<3) = 2|8 = 10

static void test_known_values_2d_2bit() {
    ame::AcousticKey k(2, 2);
    check(k.encode({1.0, 0.0}) == 5,  "encode([1,0]) with (2,2) == 5");
    check(k.encode({0.0, 1.0}) == 10, "encode([0,1]) with (2,2) == 10");
    check(k.encode({0.0, 0.0}) == 0,  "encode([0,0]) with (2,2) == 0");
    check(k.encode({1.0, 1.0}) == maxKey(2, 2),
          "encode([1,1]) with (2,2) == maxKey(2,2)=15");
}

static void test_dimensions_are_independent() {
    // [1,0] and [0,1] must produce DIFFERENT keys even though the Euclidean
    // magnitude is the same — the Morton code preserves which dimension
    // carries the value.
    ame::AcousticKey k(3, 4);
    const std::uint64_t k100 = k.encode({1.0, 0.0, 0.0});
    const std::uint64_t k010 = k.encode({0.0, 1.0, 0.0});
    const std::uint64_t k001 = k.encode({0.0, 0.0, 1.0});
    check(k100 != k010 && k100 != k001 && k010 != k001,
          "unit vectors on different dimensions give distinct keys");
}

// ── key stays within [0, maxKey] ──────────────────────────────────────────────

static void test_key_in_valid_range() {
    // Default configuration from main.cpp: 6 dimensions × 10 bits = 60 bits.
    ame::AcousticKey k(6, 10);
    const std::uint64_t mk = maxKey(6, 10);     // (1<<60)-1

    const std::vector<std::vector<double>> cases{
        {0.81, 0.22, 0.73, 0.51, 0.62, 0.31},  // plan §11 example
        {0.0,  0.0,  0.0,  0.0,  0.0,  0.0},
        {1.0,  1.0,  1.0,  1.0,  1.0,  1.0},
        {0.5,  0.5,  0.5,  0.5,  0.5,  0.5},
        {0.1,  0.9,  0.2,  0.8,  0.3,  0.7},
    };
    for (const auto& feat : cases) {
        const std::uint64_t key = k.encode(feat);
        check(key <= mk, "key is within [0, maxKey] for (6,10) configuration");
    }
}

// ── locality property ────────────────────────────────────────────────────────
//
// Morton codes preserve spatial locality in an approximate sense: vectors
// that are far apart in feature space should generally produce larger key
// differences than vectors that are close.
//
// We test a concrete, unambiguous case (plan §43: "verify empirically that
// acoustically close tracks appear close in ordering"):
//
//   dims=2, bits=4 (maxVal=15)
//   quantize formula: (uint64_t)(v * 15 + 0.5)  — truncation after +0.5
//
//   reference = [0.1, 0.1]:  q=[2, 2]   interleave → 12
//     quantize(0.10) = (uint64_t)(1.5+0.5) = (uint64_t)(2.0) = 2
//     2 = 0b0010 → interleave([2,2]):
//       b=1,d=0: bit1(2)=1@pos2; b=1,d=1: bit1(2)=1@pos3 → 4+8 = 12
//
//   close = [0.14, 0.1]: q=[2, 2]  (same bucket, 0.14*15+0.5=2.6 → 2)  → 12
//
//   medium = [0.4, 0.4]:  q=[6, 6]
//     quantize(0.40) = (uint64_t)(6.0+0.5) = (uint64_t)(6.5) = 6
//     6 = 0b0110 → interleave([6,6]):
//       b=1: 1@2,1@3 → 12;  b=2: 1@4,1@5 → 48  → total 60
//
//   far = [0.9, 0.9]:  q=[14,14]
//     quantize(0.90) = (uint64_t)(13.5+0.5) = (uint64_t)(14.0) = 14
//     14 = 0b1110 → interleave([14,14]):
//       b=1: 12;  b=2: 48;  b=3: 192  → total 252
//
//   |ref − close|  = 0
//   |ref − medium| = 48
//   |ref − far|    = 240
//
//   Key distance grows with Euclidean distance. ✓

static void test_locality_key_distance_grows_with_euclidean_distance() {
    ame::AcousticKey k(2, 4);

    const std::uint64_t key_ref    = k.encode({0.10, 0.10});
    const std::uint64_t key_close  = k.encode({0.14, 0.10});  // same bucket
    const std::uint64_t key_medium = k.encode({0.40, 0.40});
    const std::uint64_t key_far    = k.encode({0.90, 0.90});

    auto absdiff = [](std::uint64_t a, std::uint64_t b) {
        return a > b ? a - b : b - a;
    };

    const auto d_close  = absdiff(key_ref, key_close);
    const auto d_medium = absdiff(key_ref, key_medium);
    const auto d_far    = absdiff(key_ref, key_far);

    check(d_close < d_medium, "close vector has smaller key distance than medium vector");
    check(d_medium < d_far,   "medium vector has smaller key distance than far vector");

    // Concrete values: quantize uses truncation after +0.5 (round-to-nearest
    // for positive values; ties truncate down).
    check(key_ref    == 12,  "ref [0.1,0.1] → key 12");
    check(key_close  == 12,  "close [0.14,0.1] → same bucket → key 12");
    check(key_medium == 60,  "medium [0.4,0.4] → q=[6,6] → key 60");
    check(key_far    == 252, "far [0.9,0.9] → q=[14,14] → key 252");
}

// ── monotonicity along a single axis ─────────────────────────────────────────
//
// Increasing a single coordinate while keeping all others fixed should
// non-decreasingly increase (or keep equal) the Morton key — the partial
// ordering guarantee that makes the Skip List window strategy valid.

static void test_monotone_single_axis() {
    ame::AcousticKey k(2, 6);   // 12 bits total, 64 buckets per dimension

    // Sweep dimension 0 from 0 to 1 in steps, keeping dim 1 fixed at 0.5.
    std::uint64_t prev = 0;
    bool everIncreased = false;
    for (int i = 0; i <= 20; ++i) {
        const double x = i / 20.0;
        const std::uint64_t key = k.encode({x, 0.5});
        check(key >= prev, "key is non-decreasing as dim 0 increases");
        if (key > prev) everIncreased = true;
        prev = key;
    }
    check(everIncreased, "key strictly increases somewhere as dim 0 sweeps 0→1");
}

// ── plan example ─────────────────────────────────────────────────────────────
//
// The plan (§11) shows the 6-dimensional default: (6, 10) configuration
// producing quantized values like [829, 225, 747, 522, 634, 317].
// We verify that the encoder produces a non-zero, bounded key.

static void test_plan_example_6d_10bit() {
    ame::AcousticKey k(6, 10);

    // Normalized version of the plan's example values (they were already
    // quantized; we reverse-normalize to [0, 1] by dividing by maxVal=1023).
    const double mv = 1023.0;
    const std::vector<double> features{
        829.0 / mv, 225.0 / mv, 747.0 / mv,
        522.0 / mv, 634.0 / mv, 317.0 / mv
    };

    const std::uint64_t key = k.encode(features);
    check(key > 0,             "plan §11 example features yield a non-zero key");
    check(key <= maxKey(6,10), "plan §11 example key is within valid range");
}

// ── main ──────────────────────────────────────────────────────────────────────

int main() {
    test_same_features_same_key();
    test_zero_features_give_key_zero();
    test_max_features_give_max_key();
    test_clamping_below_zero();
    test_clamping_above_one();
    test_short_feature_vector_padded_with_zeros();
    test_known_values_2d_2bit();
    test_dimensions_are_independent();
    test_key_in_valid_range();
    test_locality_key_distance_grows_with_euclidean_distance();
    test_monotone_single_axis();
    test_plan_example_6d_10bit();

    std::cout << "test_acoustic_key: all tests passed\n";
    return 0;
}
