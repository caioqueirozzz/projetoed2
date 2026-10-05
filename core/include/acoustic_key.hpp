#pragma once

#include <cstdint>
#include <vector>

namespace ame {

/// Builds a 1-D ord* key from a multidimensional acoustic feature vector so
/// that acoustically similar tracks tend to land in nearby regions of the
/// Skip List.
///
/// Pipeline: normalize -> select principal dimensions -> quantize ->
/// interleave bits (Morton / Z-order) -> uint64_t.
class AcousticKey {
public:
    /// @param dimensions  number of feature dimensions to interleave.
    /// @param bitsPerDim  quantization resolution per dimension.
    ///        dimensions * bitsPerDim must be <= 64.
    AcousticKey(int dimensions, int bitsPerDim);

    /// Compute the Morton-encoded key from a (normalized) feature vector.
    /// Only the first `dimensions` entries of `features` are used.
    std::uint64_t encode(const std::vector<double>& features) const;

private:
    int dimensions_;
    int bitsPerDim_;

    /// Quantize a normalized value in [0, 1] to an integer in [0, 2^bits - 1].
    std::uint64_t quantize(double normalizedValue) const;

    /// Interleave the low `bitsPerDim_` bits of each quantized coordinate.
    std::uint64_t interleave(const std::vector<std::uint64_t>& coords) const;
};

}  // namespace ame
