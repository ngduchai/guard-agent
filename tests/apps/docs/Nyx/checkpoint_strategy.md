# Nyx Checkpoint Strategy

## Reference Implementation

Nyx uses AMReX's built-in checkpoint/restart infrastructure, identical in mechanism to other AMReX-based codes. The checkpoint captures the full cosmological simulation state, including gas hydrodynamic variables, dark matter particles, gravitational potential, and cosmological parameters (scale factor, Hubble rate). Checkpointing is triggered at user-specified step intervals or redshift values. Restart reconstructs the AMR hierarchy and all associated data, then resumes the time-stepping loop.

## Checkpoint Library

- **AMReX native checkpoint**: No external library required. Uses AMReX's `AmrLevel::checkPoint` and `AmrLevel::restart` mechanisms.
- **Format**: Directory-based structure with:
  - `Header` file containing simulation metadata, cosmological state, time step info
  - Per-level subdirectories with binary MultiFab files for gas state and gravity data
  - Particle checkpoint files for dark matter (and any other particle species)
- **I/O backend**: Coordinated POSIX I/O with configurable number of writers (`amr.checkpoint_nfiles`). Supports asynchronous output.

## What Is Checkpointed

- **Gas conserved state**: Density, momentum (3 components), total energy, and species fractions (e.g., electron fraction) on every AMR level -- both `S_old` and `S_new`
- **Gravitational potential**: `phi_old` and `phi_new` on every AMR level
- **Dark matter particles**: All particle attributes (position, velocity, mass, ID, CPU) for every particle on every level
- **AMR hierarchy**: BoxArray and DistributionMapping for each level, refinement ratios
- **Cosmological state**: Current scale factor `a`, Hubble parameter, comoving box size
- **Time-stepping state**: Current step number, simulation time, dt at each level, subcycling counters
- **Heating/cooling state**: If tabulated heating/cooling is used, the current ionization/thermal state

## Where Checkpoints Are Placed

Checkpoints are placed **at the end of a complete coarse time step**, after all subcycled fine-level steps have completed and the AMR hierarchy is synchronized. This ensures consistency between levels and between gas and particle states.

- `amr.check_int = N` -- checkpoint every N coarse steps
- `amr.check_per = T` -- checkpoint at simulation time intervals
- `nyx.plot_z_values` -- can trigger output at specific redshifts
- Output directory prefix: `amr.check_file = chk` (default), producing `chk00050/`, `chk00100/`, etc.
- Old checkpoints can be automatically removed to save space (`amr.checkpoint_files_output`).

## Restart Logic

1. Specify `amr.restart = chk00100/` in the input file
2. AMReX reads the `Header` to reconstruct the number of levels, box arrays, and distribution mappings
3. Gas state MultiFabs (`S_old`, `S_new`) are allocated and read from binary files for each level
4. Gravitational potential MultiFabs are restored
5. Dark matter particles are read and distributed to ranks based on the restored mapping
6. Cosmological parameters (scale factor, Hubble rate) are restored
7. The gravity solver recomputes any derived quantities (grad_phi) from the restored potential
8. Time stepping resumes from step `n+1`
9. If restarting on a different number of ranks, AMReX handles redistribution automatically

## Checkpoint Overhead

- **Storage cost**: Proportional to total state size. A simulation using 40 GB of memory produces checkpoints of approximately 30-50 GB (particle data is typically smaller on disk than in memory due to fewer scratch arrays being checkpointed).
- **Time cost**: I/O-bound. On parallel file systems, a 40 GB checkpoint with 512 ranks typically takes 10-40 seconds. The `amr.checkpoint_nfiles` parameter limits the number of simultaneous writers to avoid file system contention (default is 64).
- **Frequency**: Typical production cosmological runs checkpoint every 100-500 steps, or at specific redshift milestones. At 20 seconds per checkpoint and 0.5 seconds per step, checkpointing every 200 steps adds ~0.02% overhead.
- **Disk management**: Long cosmological runs spanning many expansion factors may require significant disk space. Users typically keep only the last 2-3 checkpoints and rely on plotfiles for intermediate analysis.
