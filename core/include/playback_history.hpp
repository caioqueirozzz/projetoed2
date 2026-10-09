#pragma once

#include "splay_tree.hpp"

namespace ame {

struct PlaybackEntry {
    int trackId;
    int playCount;
    std::uint64_t lastPlayOrder;
};

// Session-local history. Only playback adds entries or increments counts.
// Lookup uses the Splay Tree; chronological display never rearranges it.
class PlaybackHistory {
public:
    PlaybackEntry play(int trackId);
    const SplayNode* search(int trackId);
    std::vector<PlaybackEntry> recent() const;
    const SplayTree& tree() const { return tree_; }
    std::uint64_t totalPlays() const { return totalPlays_; }

private:
    SplayTree tree_;
    std::uint64_t totalPlays_ = 0;
};

}  // namespace ame
