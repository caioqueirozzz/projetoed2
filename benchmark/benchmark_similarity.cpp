#include "bench_support.hpp"
#include "acoustic_key.hpp"
#include "acoustic_search.hpp"
#include "dataset.hpp"
#include <iostream>
#include <numeric>
#include <random>
#include <set>
int main(int argc,char** argv) {
 try {
    const bool synthetic=argc>1&&std::string(argv[1])=="--synthetic";
    const auto input=argc>1?std::filesystem::path(argv[1]):std::filesystem::path(AME_SOURCE_ROOT)/"data/processed/tracks_processed.csv";
    const auto output=argc>2?std::filesystem::path(argv[2]):std::filesystem::path(AME_SOURCE_ROOT)/"benchmark/results"/(synthetic?"benchmark_recall_synthetic.csv":"benchmark_recall.csv");
    const int repeats=argc>3?std::stoi(argv[3]):3;
    if(repeats<1)throw std::invalid_argument("repeats must be positive");
    std::vector<ame::Track> tracks;
    if(synthetic) {
        std::mt19937 rng(42);std::uniform_real_distribution<double>d(0,1);ame::AcousticKey key(6,10);
        for(int i=0;i<5000;++i){ame::Track t;t.id=i+1;for(int j=0;j<44;++j)t.features.push_back(d(rng));t.acousticKey=key.encode(t.features);tracks.push_back(t);}
    } else tracks=ame::loadTracksCsv(input.string());
    if(tracks.size()<2)throw std::invalid_argument("At least two tracks required");
    if(output.has_parent_path())std::filesystem::create_directories(output.parent_path());
    auto csv=openCsv(output);
    csv<<"mode,num_candidates,repeat,seed,recall_at_10,avg_query_ms,brute_force_ms,dataset_size,queries,top_k,dataset_source,avg_evaluated,avg_pruned,index_build_ms\n";
    const int count=tracks.size(),queries=std::min(100,count),k=std::min(10,count-1);
    for(int rep=0;rep<repeats;++rep) {
        const unsigned seed=42+rep;auto start=BenchClock::now();ame::AcousticSearch engine(tracks,seed);const double buildMs=benchMs(start);
        std::vector<int> ids(count);std::iota(ids.begin(),ids.end(),0);std::mt19937 rng(seed);std::shuffle(ids.begin(),ids.end(),rng);ids.resize(queries);
        std::set<int> budgets;for(int c:{50,100,250,500,1000,2500,5000,count-1})budgets.insert(std::min(c,count-1));
        for(const std::string mode:{"approx","exact"})for(int c:budgets) {
            // The exact search treats the window as a seed, not a quality limit.
            if(mode=="exact"&&c!=std::min(500,count-1))continue;
            double recall=0,elapsed=0,brute=0,evaluated=0,pruned=0;
            for(int i:ids) {
                auto r=engine.search(tracks[i].id,c,k,mode=="exact",true);
                recall+=r.recall;elapsed+=r.totalMs;brute+=r.bruteMs;evaluated+=r.candidates;pruned+=r.pruned;
            }
            csv<<mode<<','<<c<<','<<rep<<','<<seed<<','<<recall/queries<<','<<elapsed/queries<<','<<brute/queries<<','<<count<<','<<queries<<','<<k<<','<<(synthetic?"synthetic":"processed_csv")<<','<<evaluated/queries<<','<<pruned/queries<<','<<buildMs<<'\n';
        }
    }
    std::cout<<"Similarity benchmark: "<<output<<'\n';
 } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
