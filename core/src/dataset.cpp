#include "dataset.hpp"
#include "acoustic_key.hpp"

#include <cmath>
#include <fstream>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

namespace ame {
namespace {
// Read a complete RFC-4180 record, including quoted newlines and escaped quotes.
bool readRecord(std::istream& input, std::vector<std::string>& fields) {
    fields.clear();
    std::string field;
    bool quoted = false, closed = false, any = false;
    char c;
    while (input.get(c)) {
        any = true;
        if (quoted) {
            if (c == '"') {
                if (input.peek() == '"') { input.get(); field += '"'; }
                else { quoted = false; closed = true; }
            } else field += c;
        } else if (c == ',') {
            fields.push_back(field); field.clear(); closed = false;
        } else if (c == '\n' || c == '\r') {
            if (c == '\r' && input.peek() == '\n') input.get();
            fields.push_back(field);
            return true;
        } else if (closed) {
            throw std::runtime_error("Unexpected character after closing CSV quote");
        } else if (c == '"') {
            if (!field.empty()) throw std::runtime_error("Unexpected quote in CSV field");
            quoted = true;
        } else field += c;
    }
    if (quoted) throw std::runtime_error("Unterminated quoted CSV field");
    if (any) fields.push_back(field);
    return any;
}

std::vector<std::string> featureNames() {
    std::vector<std::string> names = {"rmse_mean", "zcr_mean", "spectral_centroid_mean",
                                    "spectral_bandwidth_mean", "spectral_rolloff_mean"};
    for (const auto& group : std::vector<std::pair<std::string, int>>{
            {"mfcc", 20}, {"chroma_cqt", 12}, {"spectral_contrast", 7}}) {
        for (int i = 1; i <= group.second; ++i)
            names.push_back(group.first + "_mean_" + (i < 10 ? "0" : "") + std::to_string(i));
    }
    return names;
}
}  // namespace

std::vector<Track> loadTracksCsv(const std::string& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("Cannot open CSV: " + path);
    std::vector<std::string> header;
    if (!readRecord(input, header)) throw std::runtime_error("Empty dataset CSV");
    if (header[0].compare(0, 3, "\xEF\xBB\xBF") == 0) header[0].erase(0, 3);
    std::unordered_map<std::string, std::size_t> columns;
    for (std::size_t i = 0; i < header.size(); ++i)
        if (!columns.emplace(header[i], i).second)
            throw std::runtime_error("Duplicate CSV column: " + header[i]);
    auto col = [&](const std::string& name) {
        auto it = columns.find(name);
        if (it == columns.end()) throw std::runtime_error("Missing CSV column: " + name);
        return it->second;
    };
    const auto idCol = col("track_id"), titleCol = col("title"), artistCol = col("artist"),
               genreCol = col("genre"), audioCol = col("audio_path");
    std::vector<std::size_t> featureCols;
    for (const auto& name : featureNames()) featureCols.push_back(col(name));

    AcousticKey keyer(6, 10);
    std::unordered_set<int> ids;
    std::vector<Track> tracks;
    std::vector<std::string> fields;
    std::size_t record = 1;
    while (readRecord(input, fields)) {
        ++record;
        if (fields.size() == 1 && fields[0].empty()) continue;
        try {
            if (fields.size() != header.size()) throw std::runtime_error("Wrong number of columns");
            Track track;
            std::size_t used = 0;
            track.id = std::stoi(fields[idCol], &used);
            if (used != fields[idCol].size() || track.id <= 0 || !ids.insert(track.id).second)
                throw std::runtime_error("Invalid or duplicate track_id");
            track.title = fields[titleCol];
            track.artist = fields[artistCol];
            track.genre = fields[genreCol];
            track.audioPath = fields[audioCol];
            for (auto index : featureCols) {
                const double value = std::stod(fields[index], &used);
                if (used != fields[index].size() || !std::isfinite(value) || value < 0.0 || value > 1.0)
                    throw std::runtime_error("Feature outside [0, 1] or non-finite: " + header[index]);
                track.features.push_back(value);
            }
            track.acousticKey = keyer.encode(track.features);
            tracks.push_back(std::move(track));
        } catch (const std::exception& error) {
            throw std::runtime_error("CSV record " + std::to_string(record) + ": " + error.what());
        }
    }
    if (tracks.empty()) throw std::runtime_error("CSV contains no tracks");
    return tracks;
}
}  // namespace ame
