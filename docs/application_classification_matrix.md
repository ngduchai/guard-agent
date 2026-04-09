# Application Classification Matrix: Checkpointing Perspective

A systematic classification of HPC applications by **Computation Pattern** x **State Characteristics**, with 3 representative open-source applications per cell. All applications are **C/C++ only** (no Fortran). Selected for evaluating guard-agent's capability to protect applications from MPI process failures via VeloC checkpointing.

---

## Overview

| | **Fixed-size State** | **Variable-size State** |
|---|---|---|
| **Iterative/Time-stepping** | LULESH, CoMD, miniFE | WarpX, Nyx, LAMMPS |
| **Task-parallel/DAG** | DPLASMA, Chameleon | CLAMR, deal.II |
| **Pipeline/Staged** | Palabos, Nektar++, SU2 | RAxML-NG, ExaML |
| **Irregular/Adaptive** | miniVite, AMG | AMReX, SAMRAI, Uintah |

**Total: 20 apps** (all C/C++, all pure MPI, all with vanilla + checkpointed versions available)

### Apps Dropped/Replaced from Original 24
| Original | Reason | Replacement |
|----------|--------|-------------|
| CloverLeaf | No checkpointed version | miniFE (FTI) |
| MPI-FT-Bench | Split into components | miniFE, AMG, miniVite |
| Enzo-E, SpECTRE, ChaNGa | Charm++ (not pure MPI) | CLAMR, deal.II |
| CombBLAS, libgrape-lite | No checkpointed version | AMG (FTI) |
| MPI-blastn | No checkpointed version | Dropped |
| miniAMR | No checkpointed version | Dropped |

---

## 1. Iterative/Time-stepping + Fixed-size State

The checkpoint state size is constant across iterations: fixed grids, fixed particle counts per rank.

| App | Domain | Lang | Repo | Checkpointing |
|-----|--------|------|------|---------------|
| **LULESH** | Shock hydrodynamics | C++ | https://github.com/LLNL/LULESH | SCR/VeloC integrations exist (lulesh-perm) |
| **CoMD** | Molecular dynamics | C | https://github.com/ECP-copa/CoMD | FT variant at [comd-ft](https://github.com/shashankgugnani/comd-ft); used in SCR/Reinit studies |
| **CloverLeaf** | Compressible Euler equations | C++ | https://github.com/UoB-HPC/CloverLeaf | No native (trivial to add: fixed grid arrays); used with DMTCP |

### Why fixed-size
Grid topology / atom count never changes. Per-rank arrays (coordinates, velocities, pressures, densities) are constant-count throughout the simulation. Checkpoint is just dumping fixed arrays.

### Build & Run

**LULESH**:
```bash
cmake -DWITH_MPI=On -DWITH_OPENMP=On .. && make
mpirun -np 8 ./lulesh2.0 -s 30 -i 100 -p   # ranks must be perfect cube
```

**CoMD**:
```bash
cd src-mpi && cp Makefile.vanilla Makefile && make
mpirun -np 8 ./CoMD-mpi -x 20 -y 20 -z 20 -n 100
```

**CloverLeaf**:
```bash
cmake -Bbuild -H. -DCMAKE_BUILD_TYPE=Release -DENABLE_MPI=ON -DMODEL=omp
cmake --build build
mpirun -np 8 ./build/cloverleaf
```

---

## 2. Iterative/Time-stepping + Variable-size State

The checkpoint state size changes across iterations: adaptive mesh refinement, particle migration between ranks, dynamic load balancing.

| App | Domain | Lang | Repo | Checkpointing |
|-----|--------|------|------|---------------|
| **WarpX** | Plasma PIC | C++ (AMReX) | https://github.com/BLAST-WarpX/warpx | Native AMReX checkpoint (grid + particle dirs) |
| **Nyx** | Cosmology hydro+N-body | C++ (AMReX) | https://github.com/AMReX-Astro/Nyx | Native AMReX checkpoint (grid + particle binary) |
| **LAMMPS** | Molecular dynamics | C++ | https://github.com/lammps/lammps | Native `write_restart`/`read_restart`, MPI-IO |

### Why variable-size
- **WarpX**: AMR patches added/removed + particles migrate/injected/absorbed
- **Nyx**: AMR hierarchy changes as structure forms + dark matter particles cluster non-uniformly
- **LAMMPS**: Spatial decomposition particle migration + reactive MD bond breaking/creation + `fix deposit`/`fix evaporate` changing atom counts

### Build & Run

**WarpX**:
```bash
git clone --recurse-submodules https://github.com/BLAST-WarpX/warpx.git
cmake -S warpx -B build -DWarpX_DIMS=3 && cmake --build build -j$(nproc)
```

**Nyx**:
```bash
git clone --recurse-submodules https://github.com/AMReX-Astro/Nyx.git
cmake -S . -B build -DAMReX_GPU_BACKEND=NONE && cmake --build build -j$(nproc)
```

**LAMMPS**:
```bash
cmake -S cmake -B build -DPKG_MPIIO=on && cmake --build build -j$(nproc)
```

---

## 3. Task-parallel/DAG + Fixed-size State

Independent or loosely-coupled tasks operating on fixed-size data (fixed tile sizes, fixed block decomposition).

| App | Domain | Runtime | Repo | Checkpointing |
|-----|--------|---------|------|---------------|
| **DPLASMA** | Dense linear algebra | PaRSEC + MPI | https://github.com/ICLDisco/dplasma | ABFT + diskless checkpointing |
| **Chameleon** | Dense linear algebra | StarPU/PaRSEC + MPI | https://gitlab.inria.fr/solverstack/chameleon | StarPU runtime-level FT; FTI/VeloC compatible |
| **MPI-FT-Bench** | Proxy apps (miniFE, AMG, miniVite) | MPI + FTI | https://github.com/kakulo/MPI-FT-Bench | Multi-level FTI checkpointing + ULFM/Reinit++ |

### Why fixed-size
Tile-based DAG on NB x NB blocks set at launch. All tasks operate on identically-sized tiles. DAG structure is statically determined by matrix dimensions and tile size.

### Build & Run

**DPLASMA**:
```bash
git clone --recursive https://github.com/ICLDisco/dplasma.git
cd dplasma && mkdir build && cd build
cmake .. && make -j$(nproc)
```

**MPI-FT-Bench** (e.g., miniFE with FTI):
```bash
git clone https://github.com/kakulo/MPI-FT-Bench.git
git checkout restart-fti
cd miniFE/ref/src && make   # produces miniFE.x
```

---

## 4. Task-parallel/DAG + Variable-size State

Tasks where output sizes vary, dynamic task creation, or irregular task graphs.

| App | Domain | Runtime | Repo | Checkpointing |
|-----|--------|---------|------|---------------|
| **Enzo-E / Cello** | Astrophysics AMR | Charm++ (over MPI) | https://github.com/enzo-project/enzo-e | Charm++ checkpoint/restart |
| **SpECTRE** | Numerical relativity | Charm++ (over MPI) | https://github.com/sxs-collaboration/spectre | Production checkpoint/restart with parameter overlays |
| **ChaNGa** | Cosmological N-body+SPH | Charm++ (over MPI) | https://github.com/N-BodyShop/changa | Alternating-directory checkpointing |

### Why variable-size
- **Enzo-E**: AMR octree dynamically creates/destroys mesh blocks
- **SpECTRE**: Adaptive hp-refinement changes DOFs per element (higher p-order = more data)
- **ChaNGa**: Barnes-Hut tree rebuilt each timestep; particles migrate between TreePieces

### Build & Run

**SpECTRE**:
```bash
cmake -D CHARM_ROOT=/path/to/charm -D SPECTRE_FETCH_MISSING_DEPS=ON ..
make -j$(nproc) <target_name>
```

**ChaNGa**:
```bash
# Build Charm++ first, then:
cd changa && ./configure && make
charmrun ++mpiexec ChaNGa <params>
```

---

## 5. Pipeline/Staged + Fixed-size State

Data flows through sequential processing stages; each stage produces fixed-size output.

| App | Domain | Lang | Repo | Checkpointing |
|-----|--------|------|------|---------------|
| **Palabos** | Lattice Boltzmann CFD | C++ + MPI | https://github.com/omalaspinas/palabos | Native parallel checkpoint (MPI-IO) |
| **Nektar++** | Spectral/hp element CFD | C++ + MPI | https://gitlab.nektar.info/nektar/nektar | Native checkpoint/restart (`.fld`/`.rst`, HDF5) |
| **SU2** | CFD / aerodynamic optimization | C++ + MPI | https://github.com/su2code/SU2 | Native restart files |

### Why fixed-size
Fixed mesh throughout. Each timestep is a pipeline of stages (e.g., collision -> streaming -> boundary for LBM; pressure solve -> velocity solve -> scalar transport for Nektar++). All stages produce same-size arrays.

### Build & Run

**Palabos**: `cmake .. && make` (requires MPI)

**Nektar++**:
```bash
cmake -DNEKTAR_USE_MPI=ON .. && make -j$(nproc) && make install
```

**SU2**: `meson build && cd build && ninja` (MPI auto-detected)

---

## 6. Pipeline/Staged + Variable-size State

Pipeline stages where output sizes vary (filtering, compression, variable-length records).

| App | Domain | Lang | Repo | Checkpointing |
|-----|--------|------|------|---------------|
| **RAxML-NG** | Phylogenetic inference | C++ + MPI | https://github.com/amkozlov/raxml-ng | Built-in checkpoint/restart + [fault-tolerant fork](https://github.com/lukashuebner/ft-raxml-ng) |
| **ExaML** | Exascale phylogenomics | C + MPI | https://github.com/stamatak/ExaML | Built-in checkpointing |
| **MPI-blastn** | Parallel sequence alignment | C++ + MPI | https://github.com/Bioinfo-Tools/MPI-blastn | No native (would strongly benefit) |

### Why variable-size
Tree rearrangement stages produce variable numbers of candidate topologies. Filtering/pruning reduces result sets by variable amounts. Database search produces variable hit counts per query.

**Note**: This is the **rarest** combination in traditional HPC. Pure MPI pipeline codes with variable output tend to exist in bioinformatics, not classical simulation.

### Build & Run

**RAxML-NG**: `cmake .. && make` (pre-compiled binaries also available)

**ExaML**: `cd examl && make -f Makefile.SSE3.gcc`

---

## 7. Irregular/Adaptive + Fixed-size State

Irregular computation patterns (graphs, sparse structures) but the overall data size is fixed.

| App | Domain | Lang | Repo | Checkpointing |
|-----|--------|------|------|---------------|
| **CombBLAS** | Graph analytics (BFS, SpGEMM) | C++ + MPI | https://github.com/PASSIONLab/CombBLAS | No native (would benefit) |
| **libgrape-lite** | Graph processing (PageRank, SSSP) | C++ + MPI | https://github.com/alibaba/libgrape-lite | No native (would benefit) |
| **miniVite** | Community detection (Louvain) | C++ + MPI | https://github.com/ECP-ExaGraph/miniVite | FT via MPI-FT-Bench |

### Why fixed-size
Graph/sparse matrix is loaded once and never changes. Irregular because traversal patterns are data-dependent and unpredictable (which vertices are active varies per iteration).

### Build & Run

**CombBLAS**: `cmake .. && make && make install`

**libgrape-lite**: `cmake .. && make`

**miniVite**: `make` with MPI compiler

---

## 8. Irregular/Adaptive + Variable-size State

Both irregular patterns AND changing data sizes (dynamic graphs, AMR, adaptive algorithms).

| App | Domain | Lang | Repo | Checkpointing |
|-----|--------|------|------|---------------|
| **AMReX** | AMR framework | C++ + MPI | https://github.com/AMReX-Codes/amrex | Comprehensive built-in checkpoint/restart |
| **SAMRAI** | Structured AMR infrastructure | C++ + MPI | https://github.com/LLNL/SAMRAI | Built-in `RestartManager` + HDF5 |
| **Uintah** | Task-based AMR PDE framework | C++ + MPI | https://github.com/Uintah/Uintah | Built-in checkpoint + LENO fault recovery without checkpointing |

### Why variable-size
AMR dynamically refines/coarsens mesh regions. Data layout, data size, and communication patterns all change unpredictably as the solution evolves.

### Build & Run

**AMReX**: GNU Make or CMake with `USE_MPI=TRUE`

**SAMRAI**:
```bash
git submodule init && git submodule update
cmake ../SAMRAI -DCMAKE_INSTALL_PREFIX=/path/to/install && make -j$(nproc)
```

**Uintah**: CMake-based. See https://uintah.sci.utah.edu/ for detailed instructions.

---

## Evaluation Priority for guard-agent

Recommended order for testing guard-agent, balancing coverage and ease of integration:

| Priority | App | Category | Rationale |
|----------|-----|----------|-----------|
| 1 | **CoMD** | Iter+Fixed | Simplest C code, fixed atoms, FT variant exists, ECP proxy |
| 2 | **LULESH** | Iter+Fixed | Best-studied proxy app, existing SCR/VeloC examples |
| 3 | **CloverLeaf** | Iter+Fixed | Pure C++, fixed grid, trivial checkpoint state |
| 4 | **LAMMPS** | Iter+Variable | Production code with native restart, reactive/dynamic features |
| 5 | **miniVite** | Irreg+Fixed | Graph analytics, already in MPI-FT-Bench with FTI |
| 6 | **RAxML-NG** | Pipe+Variable | Fault-tolerant fork exists, bioinformatics domain |
| 7 | **WarpX** | Iter+Variable | AMReX-based, AMR + particle migration |
| 8 | **DPLASMA** | Task+Fixed | ABFT approach, task-based runtime |
| 9 | **SpECTRE** | Task+Variable | Charm++ adaptive hp-refinement |

This covers the range from trivial (fixed arrays) to challenging (variable-size AMR + particles + irregular access), and from existing VeloC support to "no checkpoint at all." All applications are C/C++ only.
