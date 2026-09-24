#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace ame {

/// A single music track from the FMA Medium dataset.
///
/// `features` holds the selected acoustic descriptors (see plan §7, ~44 values)
/// already normalized during preprocessing. `acousticKey` is the linearized
/// Morton-style index used to order tracks inside the Skip List (see §11).
struct Track {
    int id = 0;

    std::string title;
    std::string artist;
    std::string genre;

    std::vector<double> features;

    std::uint64_t acousticKey = 0;

    std::string audioPath;
};

}  // namespace ame
