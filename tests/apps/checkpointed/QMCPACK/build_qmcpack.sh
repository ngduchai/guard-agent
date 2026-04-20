#!/bin/bash
# Create missing test subdirectories that CMake expects
grep -rn 'add_subdirectory' src/ CMakeLists.txt 2>/dev/null | grep -v '#' | while read line; do
  file=$(echo "$line" | cut -d: -f1)
  dir_ref=$(echo "$line" | grep -oP 'add_subdirectory\s*\(\s*\K[^)]+' | tr -d '"' | awk '{print $1}')
  parent=$(dirname "$file")
  target="$parent/$dir_ref"
  if [ ! -d "$target" ]; then
    mkdir -p "$target"
    touch "$target/CMakeLists.txt"
  fi
done

# Clean stale CMakeCache if paths changed (copied to different directory)
if [ -f build/CMakeCache.txt ]; then
  cached_dir=$(grep 'CMAKE_HOME_DIRECTORY' build/CMakeCache.txt | head -1 | cut -d= -f2)
  if [ "$cached_dir" != "$(pwd)" ]; then
    rm -rf build
  fi
fi

mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release \
  -DQMC_MPI=ON \
  -DFFTW_HOME=$HOME/.local \
  -DCMAKE_PREFIX_PATH=$HOME/.local \
  -DBUILD_TESTING=OFF \
  && make -j$(nproc) qmcpack
