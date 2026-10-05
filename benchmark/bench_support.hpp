#pragma once
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <vector>
#include <cstdint>
using BenchClock = std::chrono::steady_clock;
inline double benchMs(BenchClock::time_point t) { return std::chrono::duration<double,std::milli>(BenchClock::now()-t).count(); }
inline std::filesystem::path outputDir(int argc, char** argv) {
    auto dir=argc>1?std::filesystem::path(argv[1]):std::filesystem::path(AME_SOURCE_ROOT)/"benchmark/results";
    std::filesystem::create_directories(dir); return dir;
}
inline std::ofstream openCsv(const std::filesystem::path& path) {
    std::ofstream out(path); if(!out) throw std::runtime_error("Cannot write "+path.string());
    out.exceptions(std::ios::badbit|std::ios::failbit); return out;
}
struct CountLess { std::uint64_t* comparisons; template<class T> bool operator()(const T& a,const T& b) const { ++*comparisons; return a<b; } };
// Deliberately unbalanced reference BST, used only by the benchmark.
class PlainBST {
    struct Node { int id; Node* left=nullptr; Node* right=nullptr; };
    Node* root=nullptr;
public:
    std::uint64_t comparisons=0;
    ~PlainBST() { while(root) { if(root->left) {auto* n=root->left;root->left=n->right;n->right=root;root=n;} else {auto* n=root->right;delete root;root=n;} } }
    void insert(int id) { auto** p=&root; while(*p) { if(id==(*p)->id)return; p=id<(*p)->id?&(*p)->left:&(*p)->right; } *p=new Node{id}; }
    int search(int id) { auto* n=root; int depth=0; while(n) {++comparisons;if(n->id==id)return depth;n=id<n->id?n->left:n->right;++depth;}return -1; }
    static std::size_t nodeBytes() {return sizeof(Node);}
};
