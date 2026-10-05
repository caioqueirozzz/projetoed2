// Unit tests for the similarity engine.
// Includes an integration test that exercises the full search pipeline:
// AcousticKey → SkipList::nearest → topK.

#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <numeric>
#include <vector>

#include "acoustic_key.hpp"
#include "similarity.hpp"
#include "skip_list.hpp"
#include "track.hpp"

// ── helpers ───────────────────────────────────────────────────────────────────

static void check(bool cond, const char* msg) {
    if (!cond) {
        std::cerr << "FAIL: " << msg << "\n";
        std::exit(1);
    }
}

static ame::Track makeTrack(int id, std::vector<double> features) {
    ame::Track t;
    t.id       = id;
    t.features = std::move(features);
    return t;
}

// ── distance functions ────────────────────────────────────────────────────────

static void test_squared_euclidean() {
    check(ame::squaredEuclidean({0,0,0}, {3,4,0}) == 25.0,
          "squaredEuclidean: 3-4-0 triangle");
    check(ame::squaredEuclidean({1,2,3}, {1,2,3}) == 0.0,
          "squaredEuclidean: same vector is 0");
    bool rejected = false;
    try { ame::squaredEuclidean({0}, {1,0,0}); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "mismatched dimensions are rejected");
}

static void test_euclidean() {
    check(std::abs(ame::euclidean({0,0,0}, {3,4,0}) - 5.0) < 1e-12,
          "euclidean: 3-4-5 triangle");
    check(ame::euclidean({2,2}, {2,2}) == 0.0,
          "euclidean: same vector is 0");
    check(ame::euclidean({0,0}, {1,0}) == 1.0,
          "euclidean: unit distance");
}

// ── topK core behaviour ───────────────────────────────────────────────────────

static void test_topk_returns_k_closest() {
    // 5 tracks at distances 0, 0.1, 0.2, 0.5, 1.0 from the origin.
    const std::vector<ame::Track> tracks = {
        makeTrack(1, {0.0, 0.0}),
        makeTrack(2, {0.1, 0.0}),
        makeTrack(3, {0.2, 0.0}),
        makeTrack(4, {0.5, 0.0}),
        makeTrack(5, {1.0, 0.0}),
    };
    const std::vector<double> query{0.0, 0.0};
    const std::vector<int> cands{1, 2, 3, 4, 5};

    const auto res = ame::topK(query, tracks, cands, 3);

    check(res.size() == 3,         "topK returns exactly k results");
    check(res[0].trackId == 1,     "closest is id 1 (distance 0)");
    check(res[1].trackId == 2,     "second is id 2 (distance 0.1)");
    check(res[2].trackId == 3,     "third is id 3 (distance 0.2)");
    check(res[0].distance == 0.0,  "distance to self is 0");
    check(std::abs(res[1].distance - 0.1) < 1e-12, "distance to id 2 is 0.1");
    check(std::abs(res[2].distance - 0.2) < 1e-12, "distance to id 3 is 0.2");
}

static void test_topk_results_sorted_ascending() {
    const std::vector<ame::Track> tracks = {
        makeTrack(1, {0.9}),
        makeTrack(2, {0.1}),
        makeTrack(3, {0.5}),
        makeTrack(4, {0.3}),
        makeTrack(5, {0.7}),
    };
    const std::vector<double> query{0.0};
    const std::vector<int> cands{5, 4, 3, 2, 1};   // shuffled order

    const auto res = ame::topK(query, tracks, cands, 5);

    check(res.size() == 5, "topK with k == n returns all");
    for (std::size_t i = 1; i < res.size(); ++i)
        check(res[i - 1].distance <= res[i].distance,
              "results are sorted by distance (ascending)");
}

static void test_topk_fewer_candidates_than_k() {
    const std::vector<ame::Track> tracks = {
        makeTrack(1, {0.1}),
        makeTrack(2, {0.2}),
    };
    const auto res = ame::topK({0.0}, tracks, {1, 2}, 10);
    check(res.size() == 2,
          "topK returns only as many results as there are valid candidates");
}

static void test_topk_unknown_candidate_ids_skipped() {
    const std::vector<ame::Track> tracks = {makeTrack(1, {0.1})};
    const auto res = ame::topK({0.0}, tracks, {99, 100, 1, 200}, 5);
    check(res.size() == 1, "unknown candidateIds are silently skipped");
    check(res[0].trackId == 1, "known candidate still returned");
}

static void test_topk_empty_inputs() {
    const std::vector<ame::Track> tracks = {makeTrack(1, {0.5})};
    check(ame::topK({0.0}, tracks, {}, 3).empty(),   "empty candidates → empty result");
    check(ame::topK({0.0}, tracks, {1}, 0).empty(),  "k=0 → empty result");
    check(ame::topK({0.0}, {}, {1}, 3).empty(),      "empty tracks → empty result");
}

static void test_topk_distances_are_euclidean_not_squared() {
    // Verify the returned distance is sqrt(squaredEuclidean), not squaredEuclidean.
    const std::vector<ame::Track> tracks = {makeTrack(1, {3.0, 4.0})};
    const auto res = ame::topK({0.0, 0.0}, tracks, {1}, 1);

    check(res.size() == 1, "one result");
    // squaredEuclidean = 9+16 = 25; euclidean = 5.
    check(std::abs(res[0].distance - 5.0) < 1e-12,
          "returned distance is Euclidean (not squared)");
}

static void test_topk_excludes_farther_tracks() {
    // With k=2, tracks at distances 0.1, 0.2, 0.8 — only the two closest.
    const std::vector<ame::Track> tracks = {
        makeTrack(10, {0.1}),
        makeTrack(20, {0.2}),
        makeTrack(30, {0.8}),
    };
    const auto res = ame::topK({0.0}, tracks, {10, 20, 30}, 2);

    check(res.size() == 2, "topK returns at most k results");
    for (const auto& r : res)
        check(r.trackId != 30, "farthest track (id 30) is excluded");
}

// ── brute-force vs approximate (Recall@K) ───────────────
//
// When ALL tracks are passed as candidates the result is exact (ground truth).
// When only a subset is passed the result is approximate. The test verifies:
//   1. ground truth: all k results are provably the closest.
//   2. approximate: a large enough candidate window recovers all ground-truth
//      results (Recall@K = 100 % for this small dataset).

static void test_recall_full_candidate_set_equals_brute_force() {
    // 20 tracks with random-ish 4-D features.
    const int N = 20;
    std::vector<ame::Track> tracks;
    for (int i = 0; i < N; ++i) {
        const double v = i / static_cast<double>(N);
        tracks.push_back(makeTrack(i + 1, {v, 1.0 - v, v * 0.5, (1.0 - v) * 0.5}));
    }

    const std::vector<double> query{0.3, 0.7, 0.15, 0.35};   // near tracks around i=6

    // Ground truth: topK over all tracks (brute force).
    std::vector<int> allIds(N);
    std::iota(allIds.begin(), allIds.end(), 1);
    const auto exact = ame::topK(query, tracks, allIds, 5);
    check(exact.size() == 5, "brute-force returns 5 results");

    // Extract ground-truth trackIds.
    std::vector<int> exactIds;
    for (const auto& r : exact) exactIds.push_back(r.trackId);

    // Approximate: pass only half the tracks (a 50 % candidate window).
    // For this tiny dataset with a centred query, 50 % should capture all top-5.
    const std::vector<int> halfCands(allIds.begin(), allIds.begin() + 10);
    const auto approx = ame::topK(query, tracks, halfCands, 5);

    // At least some overlap with ground truth (not zero recall).
    int hits = 0;
    for (const auto& r : approx) {
        if (std::find(exactIds.begin(), exactIds.end(), r.trackId) != exactIds.end())
            ++hits;
    }
    check(hits == 5, "candidate window recovers the entire known top-5");
}

// ── full pipeline integration test ─────────────────────────────────
//
// AcousticKey → insert into SkipList → SkipList::nearest → topK
//
// This exercises exactly the initial candidate search flow with a small
// in-memory dataset to verify the components compose correctly.

static void test_pipeline_acoustic_key_skiplist_topk() {
    // 10 tracks with 2-D features spread from 0.0 to 0.9.
    const int N = 10;
    ame::AcousticKey keyer(2, 10);    // 2 dimensions × 10 bits = 20 bits
    ame::SkipList index;
    std::vector<ame::Track> tracks;

    for (int i = 0; i < N; ++i) {
        const double v = i / static_cast<double>(N);
        ame::Track t = makeTrack(i + 1, {v, 1.0 - v});
        t.acousticKey = keyer.encode(t.features);
        index.insert(t.acousticKey, t.id);
        tracks.push_back(std::move(t));
    }

    // Query: similar to track 5 (features ≈ [0.4, 0.6]).
    const std::vector<double> queryFeat{0.4, 0.6};
    const std::uint64_t queryKey = keyer.encode(queryFeat);

    // Step 1: Skip List narrows the field to a candidate window.
    const int numCandidates = 6;
    const auto candidateIds = index.nearest(queryKey, numCandidates);
    check(!candidateIds.empty(), "pipeline: Skip List returns candidates");
    check((int)candidateIds.size() <= numCandidates,
          "pipeline: candidate count respects the budget");

    // Step 2: topK re-ranks by exact distance.
    const auto results = ame::topK(queryFeat, tracks, candidateIds, 3);
    check(!results.empty(),         "pipeline: topK returns results");
    check(results.size() <= 3,      "pipeline: topK respects k=3");

    // Step 3: results must be sorted ascending.
    for (std::size_t i = 1; i < results.size(); ++i)
        check(results[i - 1].distance <= results[i].distance,
              "pipeline: results sorted by distance");

    // Step 4: the closest result should be track 5 (id=5, features=[0.4, 0.6])
    //         since the query is identical to its features.
    check(results[0].trackId == 5,          "pipeline: closest track is id 5");
    check(results[0].distance < 1e-12,      "pipeline: distance to exact match is 0");
}

// ── main ──────────────────────────────────────────────────────────────────────

int main() {
    test_squared_euclidean();
    test_euclidean();
    test_topk_returns_k_closest();
    test_topk_results_sorted_ascending();
    test_topk_fewer_candidates_than_k();
    test_topk_unknown_candidate_ids_skipped();
    test_topk_empty_inputs();
    test_topk_distances_are_euclidean_not_squared();
    test_topk_excludes_farther_tracks();
    test_recall_full_candidate_set_equals_brute_force();
    test_pipeline_acoustic_key_skiplist_topk();

    std::cout << "test_similarity: all tests passed\n";
    return 0;
}
