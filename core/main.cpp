// Line protocol. Mutations in the laboratory never modify the music catalogue.
#include "dataset.hpp"
#include "acoustic_search.hpp"
#include "splay_tree.hpp"
#include <chrono>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>

static std::unique_ptr<ame::AcousticSearch> catalogue;
static auto labSkip = std::make_unique<ame::SkipList>();
static auto labSplay = std::make_unique<ame::SplayTree>();
using Clock = std::chrono::steady_clock;
static double ms(Clock::time_point start) { return std::chrono::duration<double, std::milli>(Clock::now()-start).count(); }
static std::string js(const std::string& s) {
    std::ostringstream out; out << '"';
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c < 32) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c) << std::dec;
        else out << c;
    }
    out << '"'; return out.str();
}
static const char* step(ame::SplayStep s) {
    switch(s) { case ame::SplayStep::Zig: return "Zig"; case ame::SplayStep::ZigZig: return "ZigZig";
        case ame::SplayStep::ZigZag: return "ZigZag"; default: return "None"; }
}
static std::string steps(const ame::SplayTree& tree) {
    std::ostringstream out; out << '[';
    for (std::size_t i=0;i<tree.steps().size();++i) { if(i) out << ','; out << js(step(tree.steps()[i])); }
    out << ']'; return out.str();
}
static std::string splayState(const ame::SplayTree& tree) {
    std::ostringstream out;
    out << "\"root_id\":" << (tree.getRoot() ? tree.getRoot()->trackId : -1)
        << ",\"height\":" << tree.height() << ",\"size\":" << tree.size()
        << ",\"tree_ascii\":" << js(tree.toAscii());
    return out.str();
}
static std::string skipState(const ame::SkipList& list, bool full=false) {
    const auto& m=list.metrics();
    std::ostringstream out;
    out << "\"size\":" << list.size() << ",\"comparisons\":" << m.comparisons
        << ",\"insertions\":" << m.insertions << ",\"removals\":" << m.removals << ",\"searches\":" << m.searches;
    if(full) {
        auto levels=list.snapshot(128);
        out << ",\"levels\":[";
        for(std::size_t l=0;l<levels.size();++l) {
            if(l) out << ',';
            out << '[';
            for(std::size_t i=0;i<levels[l].size();++i) {
                if(i) out << ',';
                out << "{\"key\":" << js(std::to_string(levels[l][i].first)) << ",\"id\":" << levels[l][i].second << '}';
            }
            out << ']';
        }
        out << "],\"path\":[";
        for(std::size_t i=0;i<list.lastPath().size();++i) {
            if(i) out << ',';
            out << '[' << list.lastPath()[i].first << ',' << list.lastPath()[i].second << ']';
        }
        out << ']';
    }
    return out.str();
}
static std::string search(int id, int budget, int k, const std::string& mode, bool evaluate) {
    if(!catalogue) throw std::runtime_error("Dataset not loaded");
    if(mode!="exact" && mode!="approx") throw std::invalid_argument("Mode must be exact or approx");
    const auto r=catalogue->search(id,budget,k,mode=="exact",evaluate);
    std::ostringstream out; out << std::setprecision(17);
    out << "{\"status\":\"ok\",\"results\":[";
    for(std::size_t i=0;i<r.results.size();++i) { if(i) out << ','; out << "{\"track_id\":" << r.results[i].trackId << ",\"distance\":" << r.results[i].distance << '}'; }
    out << "],\"metrics\":{\"total_tracks\":" << catalogue->tracks().size()
        << ",\"candidates\":" << r.candidates << ",\"initial_candidates\":" << r.initialCandidates
        << ",\"skiplist_comparisons\":" << r.comparisons << ",\"skiplist_ms\":" << r.indexMs
        << ",\"similarity_ms\":" << r.similarityMs << ",\"total_ms\":" << r.totalMs
        << ",\"pruned\":" << r.pruned << ",\"visited\":" << r.visited << ",\"exact\":" << (r.exact?"true":"false")
        << ",\"recall\":" << r.recall << ",\"brute_force_ms\":" << r.bruteMs
        << ",\"acoustic_key\":" << js(std::to_string(catalogue->track(id).acousticKey)) << "}}";
    return out.str();
}
static std::string labSkipCommand(const std::string& op, std::uint64_t key, int id, std::uint64_t newKey) {
    bool success=true;
    if(op!="state") labSkip->metrics().reset();
    auto start=Clock::now();
    if(op=="reset") labSkip=std::make_unique<ame::SkipList>();
    else if(op=="insert") {
        if(id<=0) throw std::invalid_argument("ID must be positive");
        success=!labSkip->contains(key,id);
        if(success && labSkip->size()>=128) throw std::invalid_argument("Laboratory limit: 128 nodes");
        if(success) labSkip->insert(key,id);
    } else if(op=="search") success=labSkip->contains(key,id);
    else if(op=="remove") success=labSkip->remove(key,id);
    else if(op=="update") success=labSkip->update(key,id,newKey);
    else if(op!="state" && op!="traverse") throw std::invalid_argument("Unknown laboratory operation");
    const double elapsed=ms(start);
    return "{\"status\":\"ok\",\"success\":"+std::string(success?"true":"false")+",\"operation_ms\":"+std::to_string(elapsed)+","+skipState(*labSkip,true)+"}";
}
static std::string labSplayCommand(const std::string& op, int id) {
    if(op=="state") return "{\"status\":\"ok\","+splayState(*labSplay)+"}";
    const auto before=labSplay->toAscii();
    const int oldRoot=labSplay->getRoot()?labSplay->getRoot()->trackId:-1;
    labSplay->metrics().reset(); bool success=true; auto start=Clock::now();
    if(op=="reset") labSplay=std::make_unique<ame::SplayTree>();
    else if(op=="state") return "{\"status\":\"ok\","+splayState(*labSplay)+"}";
    else {
        if(id<=0) throw std::invalid_argument("ID must be positive");
        if(op=="insert" || op=="access") {
            auto* existing=labSplay->getRoot();
            while(existing && existing->trackId!=id) existing=id<existing->trackId?existing->left:existing->right;
            if(!existing && labSplay->size()>=128) throw std::invalid_argument("Laboratory limit: 128 nodes");
            if(op=="insert") labSplay->insert(id); else labSplay->access(id);
        } else if(op=="search") success=labSplay->search(id)!=nullptr;
        else if(op=="remove") success=labSplay->remove(id);
        else throw std::invalid_argument("Unknown laboratory operation");
    }
    const double elapsed=ms(start); const auto& m=labSplay->metrics();
    std::ostringstream out;
    out << "{\"status\":\"ok\",\"success\":" << (success?"true":"false") << ',' << splayState(*labSplay)
        << ",\"previous_root\":" << oldRoot << ",\"tree_before\":" << js(before)
        << ",\"steps\":" << steps(*labSplay) << ",\"rotations\":" << m.rotations
        << ",\"comparisons\":" << m.comparisons << ",\"depth_before\":" << m.lastDepthBefore
        << ",\"depth_after\":" << m.lastDepthAfter << ",\"operation_ms\":" << elapsed << '}';
    return out.str();
}
int main() {
    std::ios::sync_with_stdio(false); std::cin.tie(nullptr);
    std::string line;
    while(std::getline(std::cin,line)) {
        std::istringstream in(line); std::string cmd; in>>cmd; if(cmd.empty()) continue;
        try {
            std::string response;
            if(cmd=="load") {
                std::string path; std::getline(in>>std::ws,path);
                auto next=std::make_unique<ame::AcousticSearch>(ame::loadTracksCsv(path));
                catalogue=std::move(next);
                response="{\"status\":\"ok\",\"loaded\":"+std::to_string(catalogue->tracks().size())+"}";
            } else if(cmd=="search") {
                int id,budget,k,evaluate=0; std::string mode="exact";
                if(!(in>>id>>budget>>k)) throw std::invalid_argument("search: expected ID, candidates, K");
                if(in>>mode) { if(!(in>>evaluate)) evaluate=0; }
                response=search(id,budget,k,mode,evaluate!=0);
            } else if(cmd=="track") {
                int id; if(!(in>>id)||!catalogue) throw std::invalid_argument("track: dataset and ID required");
                response="{\"status\":\"ok\",\"acoustic_key\":"+js(std::to_string(catalogue->track(id).acousticKey))+"}";
            } else if(cmd=="skiplist_state") { ame::SkipList empty; response="{\"status\":\"ok\","+skipState(catalogue?catalogue->morton():empty)+"}"; }
            else if(cmd=="lab_skip") {
                std::string op; if(!(in>>op)) throw std::invalid_argument("Missing operation");
                unsigned long long key=0,newKey=0; int id=0;
                if(op!="state"&&op!="reset"&&op!="traverse") {
                    std::string token; if(!(in>>token>>id)||token[0]=='-') throw std::invalid_argument("Invalid key/ID");
                    std::size_t used=0; key=std::stoull(token,&used); if(used!=token.size()) throw std::invalid_argument("Invalid key");
                    if(op=="update") { if(!(in>>token)||token[0]=='-') throw std::invalid_argument("Invalid new key"); newKey=std::stoull(token,&used); if(used!=token.size()) throw std::invalid_argument("Invalid new key"); }
                }
                response=labSkipCommand(op,key,id,newKey);
            } else if(cmd=="lab_splay") {
                std::string op; int id=0; if(!(in>>op)) throw std::invalid_argument("Missing operation");
                if(op!="state"&&op!="reset"&&!(in>>id)) throw std::invalid_argument("Missing ID");
                response=labSplayCommand(op,id);
            } else if(cmd=="quit") { std::cout<<"{\"status\":\"ok\"}\n"<<std::flush; break; }
            else throw std::invalid_argument("Unknown command: "+cmd);
            std::cout<<response<<'\n'<<std::flush;
        } catch(const std::exception& e) { std::cout<<"{\"status\":\"error\",\"message\":"<<js(e.what())<<"}\n"<<std::flush; }
    }
}
