#include "playback_history.hpp"
#include <cstdlib>
#include <iostream>
#include <stdexcept>

static void check(bool condition, const char* message) {
    if (!condition) { std::cerr << message << '\n'; std::exit(1); }
}

int main() {
    ame::PlaybackHistory history;
    check(history.recent().empty() && history.totalPlays() == 0, "History starts empty");
    check(history.search(10) == nullptr, "Missing lookup does not insert");
    for (int id : {10, 20, 30, 10}) {
        history.play(id);
        check(history.tree().getRoot()->trackId == id, "Playback splays the track to the root");
    }
    auto recent = history.recent();
    check(history.tree().size() == 3 && history.totalPlays() == 4, "Repeats count without duplicate nodes");
    check(recent[0].trackId == 10 && recent[0].playCount == 2 && recent[0].lastPlayOrder == 4,
          "Most recent playback is first with its count");
    check(recent[1].trackId == 30 && recent[2].trackId == 20, "Full chronological order is preserved");
    const auto* found = history.search(20);
    check(found && found == history.tree().getRoot(), "Lookup uses splay");
    check(found->accessCount == 1 && history.totalPlays() == 4, "Lookup does not count playback");
    check(history.recent()[0].trackId == 10, "Lookup does not change playback recency");
    check(history.tree().getRoot()->trackId == 20, "Listing does not rearrange the tree");
    check(history.search(999) == nullptr && history.tree().size() == 3, "Missing track stays absent");
    for (int id : {0, -1}) {
        bool rejected = false;
        try { history.play(id); } catch (const std::invalid_argument&) { rejected = true; }
        check(rejected && history.totalPlays() == 4, "Invalid playback leaves history intact");
    }
    ame::PlaybackHistory otherSession;
    check(otherSession.recent().empty(), "Histories are isolated");
    // Production history is not subject to the 128-node laboratory limit.
    for (int id = 1; id <= 2000; ++id) otherSession.play(id);
    check(otherSession.tree().size() == 2000 && otherSession.recent()[0].trackId == 2000,
          "Large histories support iterative traversal");
    check(otherSession.search(1) && otherSession.tree().getRoot()->trackId == 1,
          "Deep lookup works");
    std::cout << "test_playback_history: all tests passed\n";
}
