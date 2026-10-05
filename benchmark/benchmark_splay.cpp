#include "bench_support.hpp"
#include "splay_tree.hpp"
#include <map>
#include <random>
#include <numeric>
#include <iostream>

int main(int argc,char** argv) {
 try {
    auto dir=outputDir(argc,argv);const int repeats=argc>2?std::stoi(argv[2]):5;
    if(repeats<1)throw std::invalid_argument("repeats must be positive");
    auto progress=openCsv(dir/"benchmark_splay_progress.csv");
    progress<<"scenario,structure,n,repeat,accesses,cumulative_comparisons,cumulative_rotations,cumulative_ms\n";
    for(const std::string scenario:{"uniform","locality"}) {
        auto csv=openCsv(dir/("benchmark_splay_"+scenario+".csv"));
        csv<<"structure,n,repeat,seed,accesses,time_ms,avg_depth,hot_avg_depth,total_rotations,avg_comparisons,memory_bytes_estimate,checksum\n";
        for(int n:{1000,5000,10000,15000,20000,25000})for(int rep=0;rep<repeats;++rep) {
            const int accesses=10000,hotSize=n/5;const unsigned seed=42+rep;
            std::mt19937 rng(seed);std::vector<int> ids(n),seq(accesses);std::iota(ids.begin(),ids.end(),1);std::shuffle(ids.begin(),ids.end(),rng);
            for(auto& id:seq) {
                if(scenario=="uniform")id=std::uniform_int_distribution<int>(1,n)(rng);
                else id=std::uniform_real_distribution<double>(0,1)(rng)<.8?std::uniform_int_distribution<int>(1,hotSize)(rng):std::uniform_int_distribution<int>(hotSize+1,n)(rng);
            }
            for(const std::string structure:{"SplayTree","BST","StdMap"}) {
                ame::SplayTree splay;PlainBST bst;std::uint64_t mapComps=0;
                std::map<int,int,CountLess> map(CountLess{&mapComps});
                for(int id:ids) {if(structure=="SplayTree")splay.insert(id);else if(structure=="BST")bst.insert(id);else map[id]=0;}
                splay.metrics().reset();mapComps=0;
                std::uint64_t checksum=0,depthSum=0,hotDepth=0,hotCount=0;
                struct Checkpoint {int accesses; std::uint64_t comparisons, rotations; double time;};
                std::vector<Checkpoint> checkpoints; checkpoints.reserve(10);
                auto start=BenchClock::now();
                for(int i=0;i<accesses;++i) {
                    int id=seq[i],depth=-1;
                    if(structure=="SplayTree") {splay.access(id);depth=splay.metrics().lastDepthBefore;checksum+=splay.getRoot()->trackId;}
                    else if(structure=="BST") {depth=bst.search(id);if(depth>=0)checksum+=id;}
                    else {auto it=map.find(id);if(it!=map.end()){++it->second;checksum+=it->first;}}
                    if(depth>=0){depthSum+=depth;if(id<=hotSize){hotDepth+=depth;++hotCount;}}
                    if((i+1)%1000==0) {
                        auto comparisons=structure=="SplayTree"?splay.metrics().comparisons:structure=="BST"?bst.comparisons:mapComps;
                        checkpoints.push_back({i+1,comparisons,splay.metrics().rotations,benchMs(start)});
                    }
                }
                double elapsed=benchMs(start);
                for (const auto& point : checkpoints) {
                    progress<<scenario<<','<<structure<<','<<n<<','<<rep<<','<<point.accesses<<','<<point.comparisons<<',';
                    if(structure!="StdMap") progress<<(structure=="SplayTree"?point.rotations:0);
                    progress<<','<<point.time<<'\n';
                }
                auto comparisons=structure=="SplayTree"?splay.metrics().comparisons:structure=="BST"?bst.comparisons:mapComps;
                std::size_t memory=structure=="SplayTree"?sizeof(splay)+n*sizeof(ame::SplayNode):structure=="BST"?sizeof(bst)+n*PlainBST::nodeBytes():sizeof(map)+n*(sizeof(std::pair<const int,int>)+4*sizeof(void*));
                csv<<structure<<','<<n<<','<<rep<<','<<seed<<','<<accesses<<','<<elapsed<<',';
                if(structure!="StdMap")csv<<double(depthSum)/accesses;
                csv<<',';if(hotCount)csv<<double(hotDepth)/hotCount;
                csv<<',';if(structure!="StdMap")csv<<(structure=="SplayTree"?splay.metrics().rotations:0);
                csv<<','<<double(comparisons)/accesses<<','<<memory<<','<<checksum<<'\n';
            }
        }
    }
    std::cout<<"Splay benchmark completed\n";
 } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
