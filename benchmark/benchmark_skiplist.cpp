#include "bench_support.hpp"
#include "skip_list.hpp"
#include <map>
#include <random>
#include <iostream>

int main(int argc,char** argv) {
 try {
    auto csv=openCsv(outputDir(argc,argv)/"benchmark_skiplist.csv");
    csv<<"structure,n,repeat,seed,operation,operations,time_ms,comparisons,memory_bytes_estimate,checksum\n";
    const int repeats=argc>2?std::stoi(argv[2]):5;
    if(repeats<1) throw std::invalid_argument("repeats must be positive");
    for(int n:{1000,5000,10000,15000,20000,25000}) for(int rep=0;rep<repeats;++rep) {
        unsigned seed=42+rep; std::mt19937_64 rng(seed);
        std::vector<std::uint64_t> keys(n);
        for(int i=0;i<n;++i) keys[i]=static_cast<std::uint64_t>(i+1)*100;
        std::shuffle(keys.begin(),keys.end(),rng);
        const int queries=100;
        auto row=[&](const char* structure,const char* op,int count,double elapsed,std::uint64_t comparisons,std::size_t memory,std::uint64_t checksum) {
            csv<<structure<<','<<n<<','<<rep<<','<<seed<<','<<op<<','<<count<<','<<elapsed<<','<<comparisons<<','<<memory<<','<<checksum<<'\n';
        };
        ame::SkipList sl(16,.5,seed);
        std::vector<std::uint64_t> vec; vec.reserve(n);
        std::uint64_t vc=0,mc=0;
        std::map<std::uint64_t,int,CountLess> map(CountLess{&mc});
        for(const std::string op:{"insert","search","nearest","update","remove"}) {
            sl.metrics().reset(); std::uint64_t checksum=0;
            auto t=BenchClock::now();
            if(op=="insert") for(int i=0;i<n;++i) sl.insert(keys[i],i);
            else for(int i=0;i<queries;++i) {
                if(op=="search") { auto* found=sl.search(keys[i]); if(found) checksum+=found->key; }
                if(op=="nearest") for(int id:sl.nearest(keys[i],100)) checksum+=keys[id];
                if(op=="update") checksum+=sl.update(keys[i],i,keys[i]+1);
                if(op=="remove") checksum+=sl.remove(keys[i]+1,i);
            }
            double elapsed=benchMs(t); row("SkipList",op.c_str(),op=="insert"?n:queries,elapsed,sl.metrics().comparisons,sl.memoryBytes(),checksum);
            vc=0; checksum=0; t=BenchClock::now();
            if(op=="insert") for(auto key:keys) vec.insert(std::lower_bound(vec.begin(),vec.end(),key,CountLess{&vc}),key);
            else for(int i=0;i<queries;++i) {
                auto it=std::lower_bound(vec.begin(),vec.end(),keys[i]+(op=="remove"),CountLess{&vc});
                if(op=="search" && it!=vec.end()) {++vc;if(*it==keys[i])checksum+=*it;}
                if(op=="nearest") {
                    auto pos=it-vec.begin(); auto begin=std::max<std::ptrdiff_t>(0,pos-50);
                    auto end=std::min<std::ptrdiff_t>(vec.size(),begin+100);begin=std::max<std::ptrdiff_t>(0,end-100);
                    for(auto j=begin;j<end;++j)checksum+=vec[j];
                }
                if(op=="update" || op=="remove") {
                    ++vc;
                    if(it!=vec.end() && *it==keys[i]+(op=="remove")) {vec.erase(it);++checksum;}
                    if(op=="update") vec.insert(std::lower_bound(vec.begin(),vec.end(),keys[i]+1,CountLess{&vc}),keys[i]+1);
                }
            }
            elapsed=benchMs(t);row("SortedVector",op.c_str(),op=="insert"?n:queries,elapsed,vc,sizeof(vec)+vec.capacity()*sizeof(std::uint64_t),checksum);
            mc=0;checksum=0;t=BenchClock::now();
            if(op=="insert") for(int i=0;i<n;++i)map.emplace(keys[i],i);
            else for(int i=0;i<queries;++i) {
                if(op=="search") {auto it=map.find(keys[i]);if(it!=map.end())checksum+=it->first;}
                if(op=="nearest") {
                    auto right=map.lower_bound(keys[i]);auto left=right;int back=0;
                    while(left!=map.begin() && back<50){--left;++back;}
                    int count=0;auto it=left;
                    for(;it!=map.end()&&count<100;++it,++count)checksum+=it->first;
                    while(count<100&&left!=map.begin()){--left;checksum+=left->first;++count;}
                }
                if(op=="update") {auto it=map.find(keys[i]);if(it!=map.end()){map.erase(it);map.emplace(keys[i]+1,i);++checksum;}}
                if(op=="remove") checksum+=map.erase(keys[i]+1);
            }
            elapsed=benchMs(t);row("StdMap",op.c_str(),op=="insert"?n:queries,elapsed,mc,sizeof(map)+map.size()*(sizeof(std::pair<const std::uint64_t,int>)+4*sizeof(void*)),checksum);
        }
    }
    std::cout<<"Skip List benchmark completed\n";
 } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
