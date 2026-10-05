#include "acoustic_search.hpp"
#include "acoustic_key.hpp"
#include "splay_tree.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <random>
#include <stdexcept>
#include <set>
#include <limits>
static void check(bool condition,const char* message) {if(!condition)throw std::runtime_error(message);}
static std::pair<int,int> validate(const ame::SplayNode* n, const ame::SplayNode* p=nullptr) {
    if(!n)return {0,-1};
    check(n->parent==p,"parent pointer");
    if(n->left)check(n->left->trackId<n->trackId,"left order");
    if(n->right)check(n->right->trackId>n->trackId,"right order");
    auto l=validate(n->left,n),r=validate(n->right,n);
    check(n->subtreeSize==1+l.first+r.first,"cached subtree size");
    check(n->subtreeHeight==1+std::max(l.second,r.second),"cached subtree height");
    return {n->subtreeSize,n->subtreeHeight};
}
int main() {
 try {
    ame::SplayTree mixed;for(int i=1;i<=4;++i)mixed.access(i);mixed.access(1);
    check(mixed.steps()==std::vector<ame::SplayStep>{ame::SplayStep::ZigZig,ame::SplayStep::Zig},"full mixed trace");
    mixed.access(1);check(mixed.steps().empty(),"no stale trace for root");
    ame::SplayTree large;for(int i=1;i<=25000;++i)large.insert(i);
    check(large.height()==24999&&large.size()==25000,"large chain cached metadata");
    check(large.toAscii().size()<12000,"bounded drawing before allocation");
    large.remove(0);large.metrics().reset();check(!large.remove(0),"missing remove");
    check(large.metrics().comparisons<=2,"repeated missing remove self-adjusts");
    ame::SplayTree random;std::mt19937 rng(123);std::set<int> present;
    for(int i=0;i<3000;++i) {
        int id=int(rng()%200)+1;switch(rng()%4){case 0:random.insert(id);present.insert(id);break;case 1:random.access(id);present.insert(id);break;case 2:check(random.remove(id)==(present.erase(id)!=0),"remove result");break;default:check((random.search(id)!=nullptr)==(present.count(id)!=0),"search result");}
        validate(random.getRoot());check(random.size()==int(present.size()),"size after operation");
    }
    ame::SkipList first(16,.5,7),second(16,.5,7);
    for(int i=0;i<100;++i){first.insert(i*3,i);second.insert(i*3,i);}
    check(first.levels()==second.levels(),"seed reproducibility");
    first.insert(3,1);check(first.size()==100,"idempotent duplicate pair");
    check(first.update(3,1,700)&&!first.contains(3,1)&&first.contains(700,1),"key update");
    ame::AcousticKey fullWidth(1,64);
    check(fullWidth.encode({1.0}) == std::numeric_limits<std::uint64_t>::max(), "64-bit quantization");
    bool rejected = false;
    try { ame::AcousticKey bad(65,1); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid dimensions rejected in Release too");
    rejected = false;
    try { fullWidth.encode({std::numeric_limits<double>::quiet_NaN()}); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "NaN quantization rejected");
    ame::AcousticKey keyer(6,10);std::uniform_real_distribution<double> dist(0,1);
    std::vector<ame::Track> tracks;
    for(int i=0;i<180;++i){ame::Track t;t.id=i*7+2;for(int d=0;d<44;++d)t.features.push_back(dist(rng));if(i%7==0)t.features.assign(44,.5);t.acousticKey=keyer.encode(t.features);tracks.push_back(t);}
    // Distances close enough to share quantization bins must not be pruned.
    tracks[1].features=tracks[0].features;tracks[1].features[0]+=1e-10;tracks[1].acousticKey=keyer.encode(tracks[1].features);
    ame::AcousticSearch engine(tracks);
    for(std::size_t q=0;q<tracks.size();q+=3)for(int k:{1,10,200})for(int budget:{1,20}) {
        std::vector<std::pair<double,int>> expected;
        for(std::size_t i=0;i<tracks.size();++i)if(i!=q){double squared=0;for(int d=0;d<44;++d){double diff=tracks[q].features[d]-tracks[i].features[d];squared+=diff*diff;}expected.push_back({squared,tracks[i].id});}
        std::sort(expected.begin(),expected.end());expected.resize(std::min<std::size_t>(k,expected.size()));
        auto r=engine.search(tracks[q].id,budget,k,true,true);
        check(r.results.size()==expected.size(),"exact result count");
        for(std::size_t i=0;i<expected.size();++i){check(r.results[i].trackId==expected[i].second,"exact ranked ID vs independent full sort");check(std::abs(r.results[i].distance-std::sqrt(expected[i].first))<1e-12,"exact distance");}
        check(r.recall==1,"recall including ties");check(r.candidates+r.pruned==tracks.size()-1,"accounting of evaluated and certified pruned");
    }
    std::cout<<"Regression cases passed: metadata, large chain, traces, absent removal, deterministic levels, exact search and ties\n";
 } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
