# LAMMPS Checkpoint Strategy

## Reference Implementation
Native `write_restart` / `read_restart` commands. Binary restart files capture the complete simulation state.

## Checkpoint Library
Native binary I/O. Supports MPI-IO for parallel writes (filename must contain `.mpiio`).

## What Is Checkpointed
- All atom data: positions, velocities, IDs, types, charges, bonds
- Simulation box geometry
- Force field parameters
- Current timestep and simulation settings
- Per-atom properties (custom per-atom arrays)

## Where Checkpoints Are Placed
Controlled by the `restart` command in the input script:
```
restart 1000 restart.*.mpiio   # every 1000 steps, alternating files
```

## Restart Logic
1. `read_restart filename` in input script
2. Restores all atom data, box, force field, timestep
3. Atoms redistributed to new domain decomposition
4. Continue with `run N` from restored timestep

## Checkpoint Overhead
- Small problems (< 1M atoms): < 1% overhead
- Large problems: I/O bound, mitigated by MPI-IO and periodic (not every-step) writing
