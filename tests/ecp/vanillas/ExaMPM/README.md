# ExaMPM
## CoPA proxy-application for the Material Point Method

ExaMPM is an ECP CoPA proxy application implementing the Material Point Method
(MPM) for fluid/solid simulation. It uses [Cabana](https://github.com/ECP-copa/Cabana)
(which in turn uses [Kokkos](https://github.com/kokkos/kokkos)) for
performance-portable particle and grid operations across CPUs and GPUs.

---

## Dependencies

### System prerequisites (assumed already installed)

| Dependency | Notes |
|------------|-------|
| CMake ≥ 3.12 | Build system |
| C++17 compiler | GCC ≥ 7 or Clang ≥ 5 |
| MPI | e.g., OpenMPI or MPICH (`mpicxx` must be on `PATH`) |
| Parallel HDF5 | Optional — enables particle output; must be **parallel** HDF5, not serial |
| wget or curl | For downloading sources |
| tar, make | Standard build tools |

> **Note on HDF5:** Cabana requires **parallel** HDF5 (compiled with MPI support).
> On Debian/Ubuntu this is `libhdf5-mpi-dev`, not `libhdf5-dev`.
> Without HDF5, the simulation runs but produces no output files.

### Libraries installed by `install_deps.sh`

| Library | Version | Notes |
|---------|---------|-------|
| **Kokkos** | 4.3.01 | C++ performance portability library |
| **Cabana** | 0.7.0  | ECP CoPA particle/grid library (`Cabana::Grid` + `Cabana::Core`) |

---

## Installing Dependencies (Kokkos + Cabana)

The `install_deps.sh` script builds Kokkos and Cabana from source and installs
them to `~/.local` (or a custom prefix). **No root/sudo privileges are required.**

MPI and HDF5 are assumed to be already installed on the system.

### Quick Start

```bash
# From the ExaMPM directory:
./install_deps.sh
```

This downloads, builds, and installs Kokkos and Cabana to `~/.local`.
The script is idempotent — it skips components that are already installed.

### Options

```
./install_deps.sh [OPTIONS]

Options:
  --prefix DIR          Installation prefix (default: ~/.local)
  --kokkos-version V    Kokkos version to install (default: 4.3.01)
  --cabana-version V    Cabana version to install (default: 0.7.0)
  --no-hdf5             Build Cabana without HDF5 support (no particle output)
  --serial-only         Build Kokkos with Serial backend only (no OpenMP)
  --force-rebuild       Force rebuild even if already installed
  -h, --help            Show this help message
```

### What the script does

1. Checks that system prerequisites are available (`cmake`, `g++`, `mpicxx`, `tar`, `make`)
2. Detects whether parallel HDF5 is available (warns if only serial HDF5 is found)
3. Downloads and builds **Kokkos** from source (Serial + OpenMP backends by default)
4. Downloads and builds **Cabana** from source (with MPI + HDF5 + Grid support)

### After installation

Add the install prefix to your environment (if not already set):

```bash
export PATH="$HOME/.local/bin:$PATH"
export LD_LIBRARY_PATH="$HOME/.local/lib:${LD_LIBRARY_PATH:-}"
```

---

## Building ExaMPM

### Using CMake

```bash
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH=~/.local
cmake --build . --parallel $(nproc)
```

If Kokkos/Cabana are installed in a non-standard location:

```bash
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH="/path/to/kokkos;/path/to/cabana"
cmake --build . --parallel $(nproc)
```

### CMake auto-discovery

The `CMakeLists.txt` automatically searches the following paths for Kokkos and
Cabana installations (in addition to any `CMAKE_PREFIX_PATH` you specify):

- `~/.local`
- `/usr/local`
- `/usr`
- `/opt/kokkos`
- `/opt/cabana`

### Build outputs

After a successful build:
- `build/examples/FreeFall` — Free-fall sphere simulation
- `build/examples/DamBreak` — Dam break fluid simulation

---

## Running

Both examples take the same arguments:

```
Usage: ./FreeFall cell_size parts_per_cell halo_cells dt t_end write_freq exec_space
       ./DamBreak cell_size parts_per_cell halo_cells dt t_end write_freq exec_space

Arguments:
  cell_size       Edge length of a computational cell (domain is unit cube)
  parts_per_cell  Particles per cell in each direction
  halo_cells      Number of halo cells
  dt              Time step size
  t_end           Simulation end time
  write_freq      Number of steps between output files
  exec_space      Execution backend: serial, openmp, cuda, hip
```

### Serial (1 MPI rank)

```bash
mpirun -np 1 ./build/examples/FreeFall 0.05 2 0 0.001 1.0 10 serial
mpirun -np 1 ./build/examples/DamBreak 0.05 2 0 0.001 1.0 10 serial
```

### OpenMP (1 MPI rank, multiple threads)

```bash
OMP_NUM_THREADS=4 mpirun -np 1 ./build/examples/FreeFall 0.05 2 0 0.001 1.0 10 openmp
OMP_NUM_THREADS=4 mpirun -np 1 ./build/examples/DamBreak 0.05 2 0 0.001 1.0 10 openmp
```

### MPI (multiple ranks)

```bash
mpirun -np 4 ./build/examples/FreeFall 0.05 2 0 0.001 1.0 10 serial
mpirun -np 4 ./build/examples/DamBreak 0.05 2 0 0.001 1.0 10 serial
```

### Quick test (short run)

```bash
mpirun -np 1 ./build/examples/FreeFall 0.05 2 0 0.001 0.25 100 serial
mpirun -np 1 ./build/examples/DamBreak 0.05 2 0 0.001 0.25 100 serial
```

---

## Output

If Cabana was built with HDF5 support, particle data is written to HDF5 files
(`particles_*.h5`) every `write_freq` steps. If built with Silo support,
output goes to Silo files instead. Without either, the simulation runs but
produces no output files (a warning is printed).

---

## Using with the VeloC Agent

This application is used to test checkpoint generation with the VeloC agent.
To use it as a checkpoint test target:

1. Install Kokkos + Cabana: `./install_deps.sh`
2. Build: `mkdir build && cd build && cmake .. && cmake --build . --parallel`
3. Run with the VeloC agent pointing to one of the example binaries:
   - `build/examples/FreeFall`
   - `build/examples/DamBreak`

---

## References

- [ExaMPM GitHub](https://github.com/ECP-copa/ExaMPM)
- [ExaMPM Wiki — Dependencies](https://github.com/ECP-copa/ExaMPM/wiki/Build#dependencies)
- [ExaMPM Wiki — Build](https://github.com/ECP-copa/ExaMPM/wiki/Build#build)
- [ExaMPM Wiki — Run](https://github.com/ECP-copa/ExaMPM/wiki/Run)
- [Cabana](https://github.com/ECP-copa/Cabana)
- [Kokkos](https://github.com/kokkos/kokkos)
