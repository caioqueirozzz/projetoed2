// Adaptive Music Explorer — C++ core entry point.
//
// This binary is the bridge the Streamlit app talks to (plan §4). For the MVP
// it will: load the processed dataset, build the Skip List over acoustic keys,
// answer similarity queries, and register accesses in the Splay Tree.
//
// For now it is a smoke-test harness that simply exercises the (stubbed) types.

#include <iostream>

#include "acoustic_key.hpp"
#include "similarity.hpp"
#include "skip_list.hpp"
#include "splay_tree.hpp"
#include "track.hpp"

int main() {
    ame::SkipList index;
    ame::SplayTree profile;
    ame::AcousticKey keyer(/*dimensions=*/6, /*bitsPerDim=*/10);

    std::cout << "Adaptive Music Explorer core — scaffold build OK\n";
    std::cout << "  skip list size:  " << index.size() << "\n";
    std::cout << "  splay height:    " << profile.height() << "\n";
    return 0;
}
