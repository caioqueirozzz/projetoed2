#include "skip_list.hpp"

#include <algorithm>
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

    node->backward = update[0] == head_ ? nullptr : update[0];
    if (node->forward[0]) node->forward[0]->backward = node;

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
    if (target->forward[0]) target->forward[0]->backward = target->backward;
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
    ++metrics_.searches;
    if (numberOfCandidates <= 0 || size_ == 0) return {};
    const int budget = std::min(numberOfCandidates, size_);
    SkipNode* pred = head_;
    for (int i = currentLevel_; i >= 0; --i) {
        while (pred->forward[i]) {
            ++metrics_.comparisons;
            if (pred->forward[i]->key >= key) break;
            pred = pred->forward[i];
        }
    }

    SkipNode* left = pred == head_ ? nullptr : pred;
    SkipNode* right = pred->forward[0];
    std::deque<int> window;
    while (left && static_cast<int>(window.size()) < budget / 2) {
        window.push_front(left->trackId);
        left = left->backward;
    }
    while (right && static_cast<int>(window.size()) < budget) {
        window.push_back(right->trackId);
        right = right->forward[0];
    }
    while (left && static_cast<int>(window.size()) < budget) {
        window.push_front(left->trackId);
        left = left->backward;
    }
    return {window.begin(), window.end()};
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
