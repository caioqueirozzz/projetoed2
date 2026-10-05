#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace ame {

/// A single music track from the FMA Medium dataset.
///
/// `features` holds the selected acoustic descriptors (44 values in the prepared FMA dataset)
/// already normalized during preprocessing. `acousticKey` is the linearized
/// Morton-style index used to order tracks inside the Skip List.
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
