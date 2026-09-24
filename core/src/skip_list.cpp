#include "skip_list.hpp"

namespace ame {

SkipList::SkipList(int maxLevel, double probability)
    : maxLevel_(maxLevel), probability_(probability) {
    // Sentinel head node spanning every level.
    head_ = new SkipNode(0, -1, maxLevel_);
}

SkipList::~SkipList() {
    SkipNode* node = head_;
    while (node != nullptr) {
        SkipNode* next = node->forward.empty() ? nullptr : node->forward[0];
        delete node;
        node = next;
    }
}

int SkipList::randomLevel() {
    // TODO: draw a geometric level in [0, maxLevel_] using probability_.
    return 0;
}

void SkipList::insert(std::uint64_t /*key*/, int /*trackId*/) {
    // TODO: standard Skip List insert; update metrics_.insertions / comparisons.
}

bool SkipList::remove(std::uint64_t /*key*/, int /*trackId*/) {
    // TODO: unlink the (key, trackId) node from every level it occupies.
    return false;
}

SkipNode* SkipList::search(std::uint64_t /*key*/) {
    // TODO: top-down search; count comparisons in metrics_.
    return nullptr;
}

std::vector<int> SkipList::nearest(std::uint64_t /*key*/, int /*numberOfCandidates*/) {
    // TODO: locate the window around `key`, then expand outward on level 1
    //       until `numberOfCandidates` trackIds are gathered.
    return {};
}

std::vector<int> SkipList::traverse() const {
    // TODO: walk the level-1 chain from head_->forward[0].
    return {};
}

std::vector<std::vector<std::uint64_t>> SkipList::levels() const {
    // TODO: collect keys per level for the Structures Lab visualization.
    return {};
}

}  // namespace ame
