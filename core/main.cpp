// Adaptive Music Explorer — C++ core bridge (plan §4, §45).
//
// Protocol: one text command per stdin line → one JSON object per stdout line.
//
// Commands (Python → C++):
//   load <csv_path>
//   search <track_id> <num_candidates> <top_k>
//   access <track_id>
//   splay_state
//   skiplist_state
//   quit
//
// Responses (C++ → Python): always one UTF-8 JSON line with a "status" key.

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <memory>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

#include "dataset.hpp"
#include "similarity.hpp"
#include "skip_list.hpp"
#include "splay_tree.hpp"
#include "track.hpp"

// ── global state ──────────────────────────────────────────────────────────────

static auto g_skipList = std::make_unique<ame::SkipList>();
static auto g_profile = std::make_unique<ame::SplayTree>();
static std::vector<ame::Track>              g_tracks;
static std::unordered_map<int, std::size_t> g_trackIdx;  // id → index in g_tracks

// ── JSON helpers ──────────────────────────────────────────────────────────────

static std::string jesc(const std::string& s) {
    std::string r;
    r.reserve(s.size() + 8);
    for (unsigned char c : s) {
        if      (c == '"')  r += "\\\"";
        else if (c == '\\') r += "\\\\";
        else if (c == '\n') r += "\\n";
        else if (c == '\r') r += "\\r";
        else if (c == '\t') r += "\\t";
        else if (c < 0x20)  { /* skip control chars */ }
        else                 r += c;
    }
    return r;
}

static std::string js(const std::string& s)  { return "\"" + jesc(s) + "\""; }
static std::string ji(long long v)            { return std::to_string(v); }
static std::string jd(double v) {
    char buf[32]; std::snprintf(buf, sizeof(buf), "%.6g", v); return buf;
}

static void send(const std::string& json) {
    std::cout << json << "\n" << std::flush;
}

static void sendError(const std::string& msg) {
    send("{\"status\":\"error\",\"message\":" + js(msg) + "}");
}

// ── utilities ─────────────────────────────────────────────────────────────────

static std::string limitAscii(const std::string& full, int maxLines = 40) {
    std::string result;
    int lines = 0;
    for (char c : full) {
        if (c == '\n' && ++lines >= maxLines) {
            result += "\n... (truncated)";
            break;
        }
        result += c;
    }
    return result;
}

static const char* stepName(ame::SplayStep s) {
    switch (s) {
        case ame::SplayStep::Zig:    return "Zig";
        case ame::SplayStep::ZigZig: return "ZigZig";
        case ame::SplayStep::ZigZag: return "ZigZag";
        default:                     return "None";
    }
}

static int splayTreeSize(ame::SplayNode* n) {
    return n ? 1 + splayTreeSize(n->left) + splayTreeSize(n->right) : 0;
}

using Clock = std::chrono::high_resolution_clock;

static double elapsedMs(Clock::time_point t0) {
    return std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
}

// Load into temporary state: an invalid CSV must preserve the current index.
static void handleLoad(const std::string& path) {
    try {
        auto tracks = ame::loadTracksCsv(path);
        auto index = std::make_unique<ame::SkipList>();
        std::unordered_map<int, std::size_t> trackIdx;
        for (std::size_t i = 0; i < tracks.size(); ++i) {
            trackIdx[tracks[i].id] = i;
            index->insert(tracks[i].acousticKey, tracks[i].id);
        }
        g_tracks = std::move(tracks);
        g_trackIdx = std::move(trackIdx);
        g_skipList = std::move(index);
        g_profile = std::make_unique<ame::SplayTree>();
        send("{\"status\":\"ok\",\"loaded\":" + ji(g_tracks.size()) + "}");
    } catch (const std::exception& error) {
        sendError(error.what());
    }
}

// ── search command ────────────────────────────────────────────────────────────
//
// Format: search <track_id> <num_candidates> <top_k>

static void handleSearch(int queryId, int numCandidates, int topK) {
    if (g_tracks.empty()) {
        sendError("Dataset not loaded — call 'load' first."); return;
    }
    auto it = g_trackIdx.find(queryId);
    if (it == g_trackIdx.end()) {
        sendError("track_id " + std::to_string(queryId) + " not in dataset"); return;
    }

    if (numCandidates <= 0 || topK <= 0) {
        sendError("Candidate count and top_k must be positive"); return;
    }
    const ame::Track& q = g_tracks[it->second];

    const auto compsBefore = g_skipList->metrics().comparisons;
    auto t0 = Clock::now();
    const auto budget = std::min<std::size_t>(numCandidates, g_tracks.size() - 1);
    auto candidates = g_skipList->nearest(q.acousticKey, static_cast<int>(budget + 1));
    candidates.erase(std::remove(candidates.begin(), candidates.end(), queryId), candidates.end());
    if (candidates.size() > budget) candidates.resize(budget);
    const double slMs  = elapsedMs(t0);
    const std::uint64_t slComps = g_skipList->metrics().comparisons - compsBefore;

    auto t1 = Clock::now();
    const auto results = ame::topK(q.features, g_tracks, candidates, topK, &g_trackIdx);
    const double simMs = elapsedMs(t1);

    std::ostringstream oss;
    oss << "{\"status\":\"ok\","
        << "\"results\":[";
    for (std::size_t i = 0; i < results.size(); ++i) {
        if (i > 0) oss << ",";
        oss << "{\"track_id\":" << results[i].trackId
            << ",\"distance\":"  << jd(results[i].distance) << "}";
    }
    oss << "],"
        << "\"metrics\":{"
        << "\"total_tracks\":"        << ji(g_tracks.size())   << ","
        << "\"candidates\":"          << ji(candidates.size())  << ","
        << "\"skiplist_comparisons\":" << ji(slComps)           << ","
        << "\"skiplist_ms\":"         << jd(slMs)               << ","
        << "\"similarity_ms\":"       << jd(simMs)              << ","
        << "\"total_ms\":"            << jd(slMs + simMs)
        << "}}";
    send(oss.str());
}

// ── access command ────────────────────────────────────────────────────────────
//
// Format: access <track_id>
//
// Registers a playback event in the Splay Tree (plan §17, §45). Returns
// per-access metrics and ASCII snapshots before/after splay for §27 views.

static void handleAccess(int trackId) {
    if (trackId <= 0 || (!g_tracks.empty() && g_trackIdx.count(trackId) == 0)) {
        sendError("Unknown or invalid track_id"); return;
    }
    std::string treeBefore = g_profile->getRoot()
        ? limitAscii(g_profile->toAscii())
        : "(empty — first access)";

    const auto mBefore = g_profile->metrics();

    g_profile->access(trackId);

    const auto mAfter = g_profile->metrics();
    const std::uint64_t accessComps = mAfter.comparisons - mBefore.comparisons;
    const std::uint64_t accessRots  = mAfter.rotations   - mBefore.rotations;

    const ame::SplayNode* root = g_profile->getRoot();
    const int playCount = root ? root->playCount : 1;
    const int rootId    = root ? root->trackId   : trackId;
    const std::string treeAfter = limitAscii(g_profile->toAscii());

    std::ostringstream oss;
    oss << "{\"status\":\"ok\","
        << "\"track_id\":"     << ji(trackId)                       << ","
        << "\"step\":"         << js(stepName(g_profile->lastStep())) << ","
        << "\"depth_before\":" << ji(mAfter.lastDepthBefore)        << ","
        << "\"depth_after\":"  << ji(mAfter.lastDepthAfter)         << ","
        << "\"play_count\":"   << ji(playCount)                      << ","
        << "\"rotations\":"    << ji(accessRots)                     << ","
        << "\"comparisons\":"  << ji(accessComps)                    << ","
        << "\"root_id\":"      << ji(rootId)                         << ","
        << "\"height\":"       << ji(g_profile->height())             << ","
        << "\"tree_before\":"  << js(treeBefore)                     << ","
        << "\"tree_after\":"   << js(treeAfter)
        << "}";
    send(oss.str());
}

// ── splay_state command ───────────────────────────────────────────────────────

static void handleSplayState() {
    const ame::SplayNode* root = g_profile->getRoot();
    const std::string tree = root ? limitAscii(g_profile->toAscii()) : "(empty)";

    std::ostringstream oss;
    oss << "{\"status\":\"ok\","
        << "\"root_id\":"    << ji(root ? root->trackId : -1)            << ","
        << "\"height\":"     << ji(g_profile->height())                    << ","
        << "\"size\":"       << ji(splayTreeSize(g_profile->getRoot()))    << ","
        << "\"tree_ascii\":" << js(tree)
        << "}";
    send(oss.str());
}

// ── skiplist_state command ────────────────────────────────────────────────────

static void handleSkipListState() {
    const auto& m = g_skipList->metrics();
    std::ostringstream oss;
    oss << "{\"status\":\"ok\","
        << "\"size\":"        << ji(g_skipList->size()) << ","
        << "\"comparisons\":" << ji(m.comparisons)     << ","
        << "\"insertions\":"  << ji(m.insertions)       << ","
        << "\"searches\":"    << ji(m.searches)
        << "}";
    send(oss.str());
}

// ── main REPL ─────────────────────────────────────────────────────────────────

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;

        std::istringstream iss(line);
        std::string cmd;
        iss >> cmd;

        if (cmd == "load") {
            std::string path;
            std::getline(iss >> std::ws, path);
            if (path.empty()) { sendError("load: missing csv_path"); continue; }
            handleLoad(path);

        } else if (cmd == "search") {
            int queryId = 0, numCandidates = 500, topK = 10;
            if (!(iss >> queryId >> numCandidates >> topK)) {
                sendError("search: usage: search <track_id> <num_candidates> <top_k>");
                continue;
            }
            handleSearch(queryId, numCandidates, topK);

        } else if (cmd == "access") {
            int trackId = 0;
            if (!(iss >> trackId)) { sendError("access: usage: access <track_id>"); continue; }
            handleAccess(trackId);

        } else if (cmd == "splay_state") {
            handleSplayState();

        } else if (cmd == "skiplist_state") {
            handleSkipListState();

        } else if (cmd == "quit") {
            send("{\"status\":\"ok\"}");
            std::exit(0);

        } else {
            sendError("Unknown command: " + cmd);
        }
    }
    return 0;
}
