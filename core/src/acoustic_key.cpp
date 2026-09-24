#include "acoustic_key.hpp"

namespace ame {

AcousticKey::AcousticKey(int dimensions, int bitsPerDim)
    : dimensions_(dimensions), bitsPerDim_(bitsPerDim) {
    // Invariant expected by encode(): dimensions_ * bitsPerDim_ <= 64.
}

std::uint64_t AcousticKey::quantize(double /*normalizedValue*/) const {
    // TODO: map [0, 1] -> [0, 2^bitsPerDim_ - 1] with clamping.
    return 0;
}

std::uint64_t AcousticKey::interleave(const std::vector<std::uint64_t>& /*coords*/) const {
    // TODO: Morton / Z-order bit interleaving of the quantized coordinates.
    return 0;
}

std::uint64_t AcousticKey::encode(const std::vector<double>& /*features*/) const {
    // TODO: quantize the first dimensions_ features, then interleave().
    return 0;
}

}  // namespace ame
