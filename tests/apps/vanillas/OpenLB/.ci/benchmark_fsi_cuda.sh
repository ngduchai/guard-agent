#!/usr/bin/env nix
#!nix develop ../.#env-gcc-openmpi-cuda --command bash

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/run/opengl-driver/lib
export CUDA_ARCH=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -n 1 | grep -o [0-9] | tr -d '\n')
export CUDA_VISIBLE_DEVICES=0

echo "Testing on $(nvidia-smi --query-gpu=name --format=csv,noheader --id=1)"

make

cd examples/fsi/rigidValve2d
make

./rigidValve2d --RESOLUTION 40 --VTK_ENABLED 0

tail -n 1 tmp/gnuplotData/data/valve_n40.csv | grep -qE '24.49075317382812;-0.6667[0-9]+'
