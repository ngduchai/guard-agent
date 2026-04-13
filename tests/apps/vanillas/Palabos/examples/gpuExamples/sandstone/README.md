# Pore-level flow through a Berea sandstone

Simulates a single-phase flow through a fully resolved porous media. A 400x400x400 Berea sandstone is used as a model and replicated periodically to fill a larger space.

## Usage
Compilation:

    cd build
    export CXX=nvc++
    make -j

Execution:

- Before running, put the file "Berea.ascii" in the execution directory. File can be downloaded at https://www.dropbox.com/s/6mf545fva4e7hf2/Berea.ascii?dl=0
- Execute in benchmark mode:  `mpirun -np numNodes ./sandstone 1 [nx] [ny] [nz]`
- Execute in production mode (produces VTK files):  `mpirun -np numNodes ./sandstone 0 [nx] [ny] [nz]`

## Performance-critical GPU code

Computations: `src/atomicBlock/atomicAcceleratedLattice3D.hh` line 641.
packing: `src/atomicBlock/atomicAcceleratedLattice3D.hh` line 1319.
unpacking: `src/atomicBlock/atomicAcceleratedLattice3D.hh` line 1968.

Packing and unpacking are executed multiple times with different pieces. This loop is found in `src/parallelism/parallelBlockCommunicator3D.cpp` at line 484.

## Ongoing improvements
- Current version sets up the domain on CPU first, leading to a long setup time (typically around 10 minutes). This is being replaced by a setup directly on GPU.
