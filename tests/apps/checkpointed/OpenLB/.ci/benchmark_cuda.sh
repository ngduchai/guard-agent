#!/usr/bin/env nix
#!nix develop ../.#env-cuda --command bash

export USE_EMBEDDED_DEPENDENCIES=ON
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/run/opengl-driver/lib
export CUDA_ARCH=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -n 1 | grep -o [0-9] | tr -d '\n')
export CUDA_VISIBLE_DEVICES=1

echo "Testing on $(nvidia-smi --query-gpu=name --format=csv,noheader --id=1)"

make -j8

make testPoiseuille2DBGK

pushd examples/laminar/cavity3dBenchmark
make
for run in {1..5}; do
    ./cavity3d --RESOLUTION 100 --TIME_STEPS 1000 --VTK_ENABLED 0 | tail -n 1 | tee --append raw_performance.csv
done
awk -F',' '{sum+=$6; ++n} END { print "average_cavity3d_performance_n100 " sum/n }' < raw_performance.csv > performance.txt
popd
