#include "skip_list.hpp"

#include <deque>
#include <random>

namespace ame {

// One RNG per thread so concurrent benchmarks don't share state.
static thread_local std::mt19937 rng{std::random_device{}()};

SkipList::SkipList(int maxLevel, double probability)
    : maxLevel_(maxLevel), probability_(probability) {
    head_ = new SkipNode(0, -1, maxLevel_);
}

SkipList::~SkipList() {
    SkipNode* node = head_;
    while (node) {
        SkipNode* next = node->forward[0];
        delete node;
        node = next;
    }
}

int SkipList::randomLevel() {
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    int level = 0;
    while (level < maxLevel_ - 1 && dist(rng) < probability_)
        ++level;
    return level;
}

// ── Internal helpers ──────────────────────────────────────────────────────────

// Total order on (key, trackId) so duplicate acoustic keys are stored
// unambiguously and remove() never has to guess which node to unlink.
static inline bool before(const SkipNode* n, std::uint64_t key, int trackId) {
    return n->key < key || (n->key == key && n->trackId < trackId);
}

// ── Public operations ─────────────────────────────────────────────────────────

void SkipList::insert(std::uint64_t key, int trackId) {
    std::vector<SkipNode*> update(maxLevel_ + 1);
    SkipNode* cur = head_;

    for (int i = currentLevel_; i >= 0; --i) {
        while (cur->forward[i] && before(cur->forward[i], key, trackId)) {
            ++metrics_.comparisons;
            cur = cur->forward[i];
        }
        ++metrics_.comparisons;  // the condition that stopped the inner loop
        update[i] = cur;
    }

    const int lvl = randomLevel();
    if (lvl > currentLevel_) {
        for (int i = currentLevel_ + 1; i <= lvl; ++i)
            update[i] = head_;
        currentLevel_ = lvl;
    }

    SkipNode* node = new SkipNode(key, trackId, lvl);
    for (int i = 0; i <= lvl; ++i) {
        node->forward[i] = update[i]->forward[i];
        update[i]->forward[i] = node;
    }

    ++size_;
    ++metrics_.insertions;
}

bool SkipList::remove(std::uint64_t key, int trackId) {
    std::vector<SkipNode*> update(maxLevel_ + 1);
    SkipNode* cur = head_;

    for (int i = currentLevel_; i >= 0; --i) {
        while (cur->forward[i] && before(cur->forward[i], key, trackId)) {
            ++metrics_.comparisons;
            cur = cur->forward[i];
        }
        ++metrics_.comparisons;
        update[i] = cur;
    }

    SkipNode* target = cur->forward[0];
    if (!target || target->key != key || target->trackId != trackId)
        return false;

    for (int i = 0; i <= currentLevel_; ++i) {
        if (update[i]->forward[i] != target) break;
        update[i]->forward[i] = target->forward[i];
    }
    delete target;

    while (currentLevel_ > 0 && !head_->forward[currentLevel_])
        --currentLevel_;

    --size_;
    ++metrics_.removals;
    return true;
}

SkipNode* SkipList::search(std::uint64_t key) {
    SkipNode* cur = head_;

    for (int i = currentLevel_; i >= 0; --i) {
        while (cur->forward[i] && cur->forward[i]->key < key) {
            ++metrics_.comparisons;
            cur = cur->forward[i];
        }
        ++metrics_.comparisons;
    }

    ++metrics_.searches;
    SkipNode* candidate = cur->forward[0];
    return (candidate && candidate->key == key) ? candidate : nullptr;
}

std::vector<int> SkipList::nearest(std::uint64_t key, int numberOfCandidates) {
    // Find the predecessor: the last node with acoustic key < query key.
    SkipNode* pred = head_;
    for (int i = currentLevel_; i >= 0; --i)
        while (pred->forward[i] && pred->forward[i]->key < key)
            pred = pred->forward[i];

    // Left window: walk level-0 from head to pred (inclusive), keeping only
    // the last (numberOfCandidates / 2) trackIds in a sliding deque.
    // This is O(n) but numberOfCandidates is typically 50-5000, and we only
    // do it once per query against ~25k tracks.
    const int half = numberOfCandidates / 2;
    std::deque<int> leftIds;
    if (pred != head_) {
        for (SkipNode* n = head_->forward[0]; n != pred->forward[0]; n = n->forward[0]) {
            leftIds.push_back(n->trackId);
            if ((int)leftIds.size() > half)
                leftIds.pop_front();
        }
    }

    std::vector<int> result;
    result.reserve(numberOfCandidates);

    for (int id : leftIds)
        result.push_back(id);

    // Right window: walk forward from pred->forward[0] (key >= query key).
    for (SkipNode* n = pred->forward[0]; n && (int)result.size() < numberOfCandidates; n = n->forward[0])
        result.push_back(n->trackId);

    return result;
}

std::vector<int> SkipList::traverse() const {
    std::vector<int> out;
    out.reserve(size_);
    for (SkipNode* n = head_->forward[0]; n; n = n->forward[0])
        out.push_back(n->trackId);
    return out;
}

std::vector<std::vector<std::uint64_t>> SkipList::levels() const {
    if (size_ == 0) return {};
    std::vector<std::vector<std::uint64_t>> out(currentLevel_ + 1);
    for (int lvl = 0; lvl <= currentLevel_; ++lvl)
        for (SkipNode* n = head_->forward[lvl]; n; n = n->forward[lvl])
            out[lvl].push_back(n->key);
    return out;
}

}  // namespace ame
