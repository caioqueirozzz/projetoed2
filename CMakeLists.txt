cmake_minimum_required(VERSION 3.16)
project(adaptive_music_explorer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

add_compile_options(-Wall -Wextra -Wpedantic)

# ---- Core library (Skip List, Splay Tree, similarity, acoustic key) ----------
add_library(ame_core
    core/src/skip_list.cpp
    core/src/splay_tree.cpp
    core/src/acoustic_key.cpp
    core/src/similarity.cpp
)
target_include_directories(ame_core PUBLIC core/include)

# ---- Main executable (bridge used by the Streamlit app) ----------------------
add_executable(ame_core_app core/main.cpp)
target_link_libraries(ame_core_app PRIVATE ame_core)

# ---- Tests -------------------------------------------------------------------
enable_testing()
foreach(test_name test_skiplist test_splay test_similarity)
    add_executable(${test_name} tests/${test_name}.cpp)
    target_link_libraries(${test_name} PRIVATE ame_core)
    add_test(NAME ${test_name} COMMAND ${test_name})
endforeach()

# ---- Benchmarks --------------------------------------------------------------
foreach(bench_name benchmark_skiplist benchmark_splay benchmark_similarity)
    add_executable(${bench_name} benchmark/${bench_name}.cpp)
    target_link_libraries(${bench_name} PRIVATE ame_core)
endforeach()
