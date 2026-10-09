#include "playback_history.hpp"

#include <algorithm>
#include <stdexcept>

namespace ame {

PlaybackEntry PlaybackHistory::play(int trackId) {
    if (trackId <= 0) throw std::invalid_argument("ID must be positive");
    tree_.metrics().reset();
    tree_.access(trackId);
    auto* node = tree_.getRoot();
    node->lastPlayOrder = ++totalPlays_;
    return {node->trackId, node->accessCount, node->lastPlayOrder};
}

const SplayNode* PlaybackHistory::search(int trackId) {
    if (trackId <= 0) throw std::invalid_argument("ID must be positive");
    tree_.metrics().reset();
    return tree_.search(trackId);
}

std::vector<PlaybackEntry> PlaybackHistory::recent() const {
    std::vector<PlaybackEntry> entries;
    std::vector<const SplayNode*> pending;
    if (tree_.getRoot()) pending.push_back(tree_.getRoot());
    while (!pending.empty()) {
        const auto* node = pending.back();
        pending.pop_back();
        entries.push_back({node->trackId, node->accessCount, node->lastPlayOrder});
        if (node->left) pending.push_back(node->left);
        if (node->right) pending.push_back(node->right);
    }
    std::sort(entries.begin(), entries.end(), [](const auto& a, const auto& b) {
        return a.lastPlayOrder > b.lastPlayOrder;
    });
    return entries;
}

}  // namespace ame
