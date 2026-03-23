# ExaMiniMD

ExaMiniMD is a proxy application and research vehicle for 
particle codes, in particular Molecular Dynamics (MD). Compared to 
previous MD proxy apps (MiniMD, COMD), its design is significantly more 
modular in order to allow independent investigation of different aspects.
To achieve that the main components such as force calculation, 
communication, neighbor list construction and binning are derived 
classes whose main functionality is accessed via virtual functions. 
This allows a developer to write a new derived class and drop it into the code
without touching much of the rest of the application.

These modules are included via a module header file. Those header files are
also used to inject the input parameter logic and instantiation logic into 
the main code. As an example, look at modules_comm.h in conjunction with 
comm_serial.h and comm_mpi.h. 

In the future the plan is to provide focused miniApps with a subset of the 
available functionality for specific research purposes. 

This implementation uses the [Kokkos](https://github.com/kokkos/kokkos)
programming model for performance portability across CPUs and GPUs.

# Current Capabilities

### Force Fields:
 * Lennard-Jones Cell List
 * Lennard-Jones Neighbor List
 * SNAP Full Neighbor List 

### Neighbor List:
 * 2D NeighborList creation
 * CSR NeighborList creation

### Integrator:
 * NVE (constant energy velocity-Verlet)

### Communication
 * Serial
 * MPI

### Binning:
 * Kokkos Sort Binning

### Input:
 * Restricted LAMMPS input files

---

# Dependencies

ExaMiniMD requires the following dependencies:

| Dependency | Version | Notes |
|------------|---------|-------|
| CMake      | ≥ 3.10  | Build system |
| C++ compiler | C++17 capable | GCC ≥ 7, Clang ≥ 5 |
| **Kokkos** | ≥ 3.0   | **Required** — performance portability library |
| MPI        | any     | Optional (enabled by default via `-DUSE_MPI=ON`) |

## Installing Dependencies

An optional helper script `install_deps.sh` is provided to install Kokkos
(and check for MPI) automatically.

### Quick Start (user-local install, no sudo required)

```bash
# From the ExaMiniMD directory:
./install_deps.sh
```

This installs Kokkos to `~/.local` (no root privileges needed).

### Options

```
./install_deps.sh [OPTIONS]

Options:
  --prefix DIR        Installation prefix for Kokkos (default: ~/.local)
  --kokkos-version V  Kokkos version to install (default: 4.3.01)
  --no-mpi            Skip MPI installation check
  --serial-only       Build Kokkos with Serial backend only (no OpenMP)
  --system-prefix     Install to /usr/local (requires sudo)
  -h, --help          Show this help message
```

### Manual Kokkos Installation

If you prefer to install Kokkos manually:

```bash
# Clone Kokkos
git clone https://github.com/kokkos/kokkos ~/kokkos
cd ~/kokkos

# Configure and build (OpenMP + Serial backends)
mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=~/.local \
  -DCMAKE_BUILD_TYPE=Release \
  -DKokkos_ENABLE_SERIAL=ON \
  -DKokkos_ENABLE_OPENMP=ON \
  -DCMAKE_CXX_STANDARD=17

cmake --build . --parallel $(nproc)
cmake --install .
```

### MPI

On Debian/Ubuntu:
```bash
sudo apt-get install -y libopenmpi-dev openmpi-bin
```

On RHEL/Fedora:
```bash
sudo dnf install -y openmpi-devel
```

---

# Compilation (CMake — Recommended)

ExaMiniMD uses CMake as its primary build system. The `CMakeLists.txt`
automatically searches common Kokkos install locations (`~/.local`,
`/usr/local`, `/opt/kokkos`).

## Basic Build (with MPI, OpenMP backend)

```bash
# From the ExaMiniMD directory:
mkdir build && cd build
cmake ..
cmake --build . --parallel
```

## Build without MPI (Serial only)

```bash
mkdir build && cd build
cmake .. -DUSE_MPI=OFF
cmake --build . --parallel
```

## Custom Kokkos Location

If Kokkos is installed in a non-standard location:

```bash
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH=/path/to/kokkos/install
cmake --build . --parallel
```

## CMake Options

| Option | Default | Description |
|--------|---------|-------------|
| `USE_MPI` | `ON` | Build with MPI support |
| `CMAKE_BUILD_TYPE` | `Release` | Build type (Release/Debug/RelWithDebInfo) |
| `CMAKE_PREFIX_PATH` | auto | Path to Kokkos installation |

The compiled binary is placed at `build/src/ExaMiniMD`.

---

# Compilation (GNU Make — Legacy)

ExaMiniMD also supports the Kokkos GNU Make build system. This requires
Kokkos to be cloned (not installed) and pointed to via `KOKKOS_PATH`.

```bash
git clone https://github.com/kokkos/kokkos ~/kokkos
cd src
```

Intel Sandy-Bridge CPU / Serial / MPI:
```
  make -j KOKKOS_ARCH=SNB KOKKOS_DEVICES=Serial CXX=mpicxx MPI=1
```

Intel Haswell CPU / Pthread / No MPI:
```
  make -j KOKKOS_ARCH=HSW KOKKOS_DEVICES=Pthread CXX=clang MPI=0
```

IBM Power8 CPU / OpenMP / MPI
```
  make -j KOKKOS_ARCH=Power8 KOKKOS_DEVICES=OpenMP CXX=mpicxx
```

IBM Power8 CPU + NVIDIA P100 / CUDA / MPI (OpenMPI)
```
  export OMPI_CXX=[KOKKOS_PATH]/bin/nvcc_wrapper
  make -j KOKKOS_ARCH=Power8,Pascal60 KOKKOS_DEVICES=Cuda CXX=mpicxx
```

---

# Running

ExaMiniMD reads LAMMPS-format input files. Example input files are provided
in the `input/` directory.

## Serial Mode (single process, OpenMP threads)

```bash
# From the build directory:
OMP_PROC_BIND=false ./src/ExaMiniMD -il ../input/in.lj \
  --comm-type Serial --kokkos-threads=1
```

## MPI Mode (2 processes, 12 threads each)

```bash
mpirun -np 2 -bind-to socket ./src/ExaMiniMD \
  -il ../input/in.lj --comm-type MPI --kokkos-threads=12
```

## GPU Mode (2 MPI tasks, 1 GPU each)

```bash
mpirun -np 2 -bind-to socket ./src/ExaMiniMD \
  -il ../input/in.lj --comm-type MPI --kokkos-ndevices=2
```

## Binary Dump (for checkpoint/correctness testing)

Write binary output every timestep to `ReferenceDir`:
```bash
./src/ExaMiniMD -il ../input/in.lj \
  --kokkos-threads=1 --binarydump 1 ReferenceDir
```

Check correctness every timestep against `ReferenceDir`:
```bash
./src/ExaMiniMD -il ../input/in.lj \
  --kokkos-threads=2 --correctness 1 ReferenceDir correctness.dat
```

---

# Expected Output

A successful run with `input/in.lj` (100 timesteps, 256,000 atoms) produces
output similar to:

```
Using: ForceLJNeighFull Neighbor2D CommMPI BinningKKSort
Atoms: 256000 256000

#Timestep Temperature PotE ETot Time Atomsteps/s
0 1.400000 -6.332812 -4.232820 0.000000 0.000000e+00
10 1.266963 -6.133598 -4.233161 ...
...
100 0.732072 -5.330936 -4.232833 ...

#Procs Particles | Time T_Force T_Neigh T_Comm T_Other | Steps/s Atomsteps/s ...
1 256000 | ... PERFORMANCE
```
