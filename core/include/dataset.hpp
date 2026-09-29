#pragma once

#include <string>
#include <vector>
#include "track.hpp"

namespace ame {
// Load the processed FMA CSV, validating IDs, named columns and all 44 features.
// Throws std::runtime_error on malformed input; never silently imputes values.
std::vector<Track> loadTracksCsv(const std::string& path);
}
