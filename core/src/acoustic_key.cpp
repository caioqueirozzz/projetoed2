#include "acoustic_key.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>

namespace ame {

// ── Constructor ───────────────────────────────────────────────────────────────

AcousticKey::AcousticKey(int dimensions, int bitsPerDim)
    : dimensions_(dimensions), bitsPerDim_(bitsPerDim) {
    if (dimensions <= 0 || bitsPerDim <= 0 || dimensions > 64 || bitsPerDim > 64 || dimensions > 64 / bitsPerDim)
        throw std::invalid_argument("Acoustic Key dimensions and bits must fit uint64_t");
}

// ── quantize ──────────────────────────────────────────────────────────────────
//
// Maps a normalized value in [0, 1] to an integer in [0, 2^bitsPerDim_ − 1].
// Values outside the unit interval are clamped so out-of-range features never
// cause bit-overflow in the interleaved result.
// Round-to-nearest avoids systematic bias at bucket boundaries.

std::uint64_t AcousticKey::quantize(double normalizedValue) const {
    if (!std::isfinite(normalizedValue)) throw std::invalid_argument("Non-finite acoustic feature");
    const std::uint64_t maxVal = bitsPerDim_ == 64 ? std::numeric_limits<std::uint64_t>::max() : (1ULL << bitsPerDim_) - 1;

    if (normalizedValue <= 0.0) return 0;
    if (normalizedValue >= 1.0) return maxVal;

    return static_cast<std::uint64_t>(
        static_cast<long double>(normalizedValue) * maxVal + 0.5L);
}

// ── interleave ────────────────────────────────────────────────────────────────
//
// Morton / Z-order bit interleaving: for each bit position b (0 = LSB) and
// each dimension d, the b-th bit of coords[d] lands at output position
// b*dimensions_ + d.
//
// Property exploited by the Skip List: points that are close in feature space
// tend to produce nearby keys, so a window of N candidates around the query
// key captures many acoustically similar tracks without scanning the whole
// dataset.  (Z-order is not perfect near power-of-two boundaries, but the
// large candidate window compensates for those edge cases.)

std::uint64_t AcousticKey::interleave(const std::vector<std::uint64_t>& coords) const {
    std::uint64_t result = 0;

    for (int b = 0; b < bitsPerDim_; ++b) {
        for (int d = 0; d < dimensions_; ++d) {
            const std::uint64_t bit = (coords[d] >> b) & 1ULL;
            result |= bit << (b * dimensions_ + d);
        }
    }

    return result;
}

// ── encode ────────────────────────────────────────────────────────────────────
//
// Full pipeline: normalize (assumed done upstream) → select the first
// `dimensions_` entries → quantize each → interleave bits.
//
// If `features` has fewer entries than `dimensions_`, the missing dimensions
// are treated as 0 (silence / minimum value), so short vectors always produce
// a valid key.

std::uint64_t AcousticKey::encode(const std::vector<double>& features) const {
    std::vector<std::uint64_t> coords(dimensions_);

    for (int d = 0; d < dimensions_; ++d) {
        const double val = (d < static_cast<int>(features.size()))
                           ? features[d]
                           : 0.0;
        coords[d] = quantize(val);
    }

    return interleave(coords);
}

}  // namespace ame
