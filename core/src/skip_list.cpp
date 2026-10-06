#include "skip_list.hpp"

#include <algorithm>
#include <deque>
#include <random>
#include <stdexcept>

namespace ame {

SkipList::SkipList(int maxLevel, double probability, unsigned seed)
    : maxLevel_(maxLevel), probability_(probability), rng_(seed) {
    if (maxLevel < 1 || maxLevel > 64 || !(probability > 0 && probability < 1))
        throw std::invalid_argument("Invalid Skip List parameters");
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
    while (level < maxLevel_ - 1 && dist(rng_) < probability_)
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
    lastPath_.clear();
    for (int i = currentLevel_; i >= 0; --i) {
        while (cur->forward[i]) {
            ++metrics_.comparisons;
            if (!before(cur->forward[i], key, trackId)) break;
            cur = cur->forward[i]; lastPath_.push_back({i, cur->trackId});
        }
        update[i] = cur;
    }

    if (cur->forward[0]) ++metrics_.comparisons;
    if (cur->forward[0] && cur->forward[0]->key == key && cur->forward[0]->trackId == trackId) return;
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
    lastPath_.clear();
    for (int i = currentLevel_; i >= 0; --i) {
        while (cur->forward[i]) {
            ++metrics_.comparisons;
            if (!before(cur->forward[i], key, trackId)) break;
            cur = cur->forward[i]; lastPath_.push_back({i, cur->trackId});
        }
        update[i] = cur;
    }

    SkipNode* target = cur->forward[0];
    if (target) ++metrics_.comparisons;
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

std::pair<const SkipNode*, const SkipNode*> SkipList::neighbors(std::uint64_t key) {
    ++metrics_.searches;
    lastPath_.clear();
    SkipNode* cur = head_;
    for (int i = currentLevel_; i >= 0; --i) {
        while (cur->forward[i]) {
            ++metrics_.comparisons;
            if (cur->forward[i]->key >= key) break;
            cur = cur->forward[i];
            lastPath_.push_back({i, cur->trackId});
        }
    }
    return {cur == head_ ? nullptr : cur, cur->forward[0]};
}

SkipNode* SkipList::search(std::uint64_t key) {
    auto pair = neighbors(key);
    if (pair.second) ++metrics_.comparisons;
    return pair.second && pair.second->key == key ? const_cast<SkipNode*>(pair.second) : nullptr;
}

std::vector<int> SkipList::searchAll(std::uint64_t key) {
    const auto bounds = neighbors(key);
    std::vector<int> ids;
    for (const auto* node = bounds.second; node; node = node->forward[0]) {
        ++metrics_.comparisons;
        if (node->key != key) break;
        ids.push_back(node->trackId);
    }
    return ids;
}

bool SkipList::contains(std::uint64_t key, int trackId) {
    ++metrics_.searches;
    lastPath_.clear();
    const SkipNode* cur = head_;
    for (int level = currentLevel_; level >= 0; --level) {
        while (cur->forward[level]) {
            ++metrics_.comparisons;
            if (!before(cur->forward[level], key, trackId)) break;
            cur = cur->forward[level];
            lastPath_.push_back({level, cur->trackId});
        }
    }
    const auto* candidate = cur->forward[0];
    if (candidate) ++metrics_.comparisons;
    return candidate && candidate->key == key && candidate->trackId == trackId;
}

bool SkipList::update(std::uint64_t oldKey, int trackId, std::uint64_t newKey) {
    if (!contains(oldKey, trackId)) return false;
    if (oldKey == newKey) return true;
    if (contains(newKey, trackId)) return false;
    remove(oldKey, trackId);
    insert(newKey, trackId);
    return true;
}

std::vector<int> SkipList::nearest(std::uint64_t key, int numberOfCandidates) {
    auto bounds = neighbors(key);
    if (numberOfCandidates <= 0 || size_ == 0) return {};
    const int budget = std::min(numberOfCandidates, size_);
    const SkipNode* left = bounds.first;
    const SkipNode* right = bounds.second;
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

std::vector<std::vector<std::pair<std::uint64_t, int>>> SkipList::snapshot(std::size_t limit) const {
    std::vector<std::vector<std::pair<std::uint64_t, int>>> result(currentLevel_ + 1);
    for (int level = 0; level <= currentLevel_; ++level)
        for (auto* n = head_->forward[level]; n && result[level].size() < limit; n = n->forward[level])
            result[level].push_back({n->key, n->trackId});
    return result;
}
std::size_t SkipList::memoryBytes() const {
    std::size_t bytes = sizeof(*this);
    for (auto* n = head_; n; n = n->forward[0]) bytes += sizeof(SkipNode) + n->forward.capacity() * sizeof(SkipNode*);
    return bytes + lastPath_.capacity() * sizeof(std::pair<int, int>);
}
}  // namespace ame
