# WarpX Checkpoint Strategy

## Reference Implementation

WarpX uses AMReX's built-in checkpoint/restart infrastructure. The checkpoint is triggered at regular intervals controlled by the `amr.check_int` (step interval) or `amr.check_per` (simulation time interval) input parameters. The checkpoint routine traverses all AMR levels, writing field MultiFabs, particle containers, and simulation metadata into a structured directory hierarchy. Restart is initiated by specifying `amr.restart` with the path to a checkpoint directory, which reconstructs the full simulation state before resuming the time loop.

## Checkpoint Library

- **AMReX native checkpoint**: Built into the AMReX framework. No external checkpoint library is required.
- **Format**: Each checkpoint is a directory containing:
  - A `Header` file with simulation metadata (time step, time, number of levels, box layout)
  - Per-level subdirectories with binary MultiFab data files (one file per FAB component)
  - Particle checkpoint files per species per level in AMReX's native particle format
- **I/O backend**: Uses MPI-coordinated POSIX I/O by default. Each rank writes its own data segments. AMReX also supports asynchronous output via its `AsyncOut` mechanism.

## What Is Checkpointed

- **Electromagnetic fields**: All 6 field components (Ex, Ey, Ez, Bx, By, Bz) on every AMR level, including fine-patch and coarse-patch data
- **Current density**: Jx, Jy, Jz on every level
- **Charge density**: rho on every level (if used)
- **Divergence cleaning fields**: F and G fields if divergence cleaning is active
- **PML fields**: All PML split-field components if PML boundaries are active
- **Particles**: Full particle data for every species (positions, momenta, weights, IDs) on every level
- **AMR hierarchy**: Box layout, refinement ratios, distribution mapping for each level
- **Simulation metadata**: Current time step number, simulation time, dt, geometry and domain information, boosted-frame parameters

## Where Checkpoints Are Placed

Checkpoints are placed **at the end of a full time step**, after all field solves, particle pushes, and boundary condition applications are complete. This ensures the simulation state is self-consistent and can be restarted without requiring any partial-step recovery logic.

- Placement is controlled by:
  - `amr.check_int = N` -- checkpoint every N time steps
  - `amr.check_per = T` -- checkpoint every T units of simulation time
- Output directory: `amr.check_file = chk` (default prefix), producing directories like `chk00100/`, `chk00200/`, etc.
- Multiple checkpoints can be retained or older ones can be overwritten based on configuration.

## Restart Logic

1. User specifies `amr.restart = chk00100/` in the input file
2. AMReX reads the `Header` file to reconstruct the AMR hierarchy (number of levels, box arrays, distribution mapping)
3. Field MultiFabs are allocated and populated from the binary data files for each level
4. Particle containers are rebuilt by reading particle checkpoint files; particles are distributed to the appropriate ranks based on the restored distribution mapping
5. Simulation metadata (time step counter, simulation time, dt) is restored
6. The time-stepping loop resumes from step `n+1` where `n` is the checkpointed step
7. If the number of MPI ranks differs from the original run, AMReX redistributes boxes and particles to the new rank count automatically

## Checkpoint Overhead

- **Storage cost**: Comparable to the full in-memory state. For a simulation using 100 GB of memory, a checkpoint is approximately 80-120 GB on disk (field data is written as-is in binary; particle data includes all attributes).
- **Time cost**: Checkpoint write time is I/O-bandwidth-limited. On parallel file systems (Lustre, GPFS), a 100 GB checkpoint typically takes 10-60 seconds depending on the number of ranks and file system performance. AMReX's default I/O uses coordinated writes where a subset of ranks (NFiles parameter) write to disk, reducing file system contention.
- **Frequency trade-off**: Typical production runs checkpoint every 100-1000 time steps. At 30 seconds per checkpoint and 0.1 seconds per time step, checkpointing every 100 steps adds ~0.3% overhead. Checkpointing every 10 steps would add ~3% overhead.
- **Async output**: AMReX supports asynchronous checkpoint writes that overlap I/O with computation, further reducing perceived overhead.
